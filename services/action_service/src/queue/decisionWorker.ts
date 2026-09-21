/**
 * DecisionWorker (BullMQ) — assemblage du flux complet (§7 et §10 de `main.md`) :
 *
 *   decisionQueue → décodage/validation → contexte communauté → verdict →
 *   upsert `moderation_cases` → insert `user_actions` → callback → statut livraison.
 *
 * Classification des erreurs (§11) :
 *  - métier (`InvalidJobError`, `CommunityNotFoundError`) → rethrow → job `failed`, pas de retry ;
 *  - infra (`ConfigReadError`, `HistoryWriteError`) → rethrow → job retenté par BullMQ (attempts).
 *
 * Idempotence : le upsert par `moderationCaseId` (uuid v5 déterministe) garantit
 * qu'aucun cas double/corrompu n'est écrit lors d'un re-jeu.
 */

import { Worker } from 'bullmq';
import type { Settings } from '../config/settings.js';
import { bullmqConnection } from '../config/redis.js';
import { parseDecisionJob } from '../validation/zodDecisionJob.js';
import type { DecisionJob } from '../types/job.js';
import type { UserActionEvent, DecisionProcessor } from '../service/decisionProcessor.js';
import type { ModerationCase, UserActionRecord } from '../types/case.js';
import type { CommunityRepository } from '../models/communityRepository.js';
import type { ModerationCaseRepository } from '../models/moderationCaseRepository.js';
import type { UserActionRepository } from '../models/userActionRepository.js';
import type { CallbackClient } from '../service/callbackClient.js';
import { InvalidJobError } from '../exceptions/index.js';
import type { Logger } from '../utils/logger.js';

export interface DecisionWorkerDeps {
  settings: Settings;
  /** Nom de file consommé ; défaut `settings.decisionQueueName` (injectable pour les tests). */
  queueName?: string;
  communityRepository: CommunityRepository;
  processor: DecisionProcessor;
  caseRepository: ModerationCaseRepository;
  userActionRepository: UserActionRepository;
  callbackClient: CallbackClient;
  logger: Logger;
}

export class DecisionWorker {
  private worker: Worker | null = null;

  constructor(private readonly deps: DecisionWorkerDeps) {}

  start(): void {
    const { settings, queueName, logger } = this.deps;
    this.worker = new Worker(queueName ?? settings.decisionQueueName, (job) => this.run(job.data), {
      connection: bullmqConnection(settings),
      concurrency: settings.decisionWorkerConcurrency,
    });
    this.worker.on('failed', (job, err) => {
      logger.error('decision.job.failed', { jobId: job?.id, attempts: job?.attemptsMade, err });
    });
    logger.info('decision.worker.started', {
      queue: queueName ?? settings.decisionQueueName,
      concurrency: settings.decisionWorkerConcurrency,
    });
  }

  async stop(): Promise<void> {
    if (this.worker) {
      await this.worker.close();
      this.worker = null;
    }
  }

  /** Handler exposé (appelé par BullMQ) — testable unitairement via `run`. */
  async run(raw: unknown): Promise<void> {
    const logger = this.deps.logger.child({ handler: 'decisionWorker' });

    // 1. Décodage + validation (job non conforme → failed définitif).
    let job: DecisionJob;
    try {
      job = parseDecisionJob(raw);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      logger.error('decision.job.invalid', { err: error });
      throw new InvalidJobError(`invalid decision job: ${message}`);
    }

    const jobLogger = logger.child({ jobId: `${job.batchId}:${job.content.contentId}` });
    const now = new Date();

    // 2. Contexte communauté (D-04) — fournit accountId + callbackUrl.
    const community = await this.deps.communityRepository.findByRef(job.communityRef);

    // 3. Résolution métier : verdict + attribution des sanctions par détection.
    const { verdict, userActionEvents } = await this.deps.processor.processWithEvents(job);

    // 4. Persistance historique D-02 (upsert idempotent par moderationCaseId).
    const caseRecord: ModerationCase = {
      moderationCaseId: verdict.moderationCaseId,
      communityRef: verdict.communityRef,
      accountId: community.accountId,
      contentId: verdict.contentId,
      contentType: verdict.contentType,
      userRef: verdict.userRef,
      contentTimestamp: new Date(job.content.timestamp),
      detections: verdict.detections,
      status: verdict.status,
      decision: verdict.decision,
      contentActions: verdict.contentActions,
      userActions: verdict.userActions,
      needsReview: verdict.needsReview,
      filtersReport: job.filtersReport,
      callback: {
        url: community.callbackUrl,
        status: 'pending',
        attempts: 0,
        lastError: null,
        deliveredAt: null,
      },
      createdAt: now,
      updatedAt: now,
    };
    await this.deps.caseRepository.upsert(caseRecord);

    // 5. Journal des sanctions utilisateur (par détection déclenchante).
    const actionRecords = this.buildUserActionRecords(
      verdict.communityRef,
      verdict.userRef,
      verdict.moderationCaseId,
      userActionEvents,
      now
    );
    if (actionRecords.length > 0) {
      await this.deps.userActionRepository.insertMany(actionRecords);
    }

    // 6. Callback client + statut de livraison persisté.
    const delivery = await this.deps.callbackClient.deliver(community.callbackUrl, verdict);
    await this.deps.caseRepository.updateCallback(verdict.moderationCaseId, {
      url: community.callbackUrl,
      status: delivery.status,
      attempts: delivery.attempts,
      lastError: delivery.lastError,
      deliveredAt: delivery.deliveredAt,
    });

    if (delivery.status === 'delivered') {
      jobLogger.info('decision.job.completed', {
        moderationCaseId: verdict.moderationCaseId,
        decision: verdict.decision,
        needsReview: verdict.needsReview,
        contentActions: verdict.contentActions.length,
        userActions: verdict.userActions.length,
      });
    } else {
      jobLogger.warn('decision.job.completed.callback_failed', {
        moderationCaseId: verdict.moderationCaseId,
        attempts: delivery.attempts,
        lastError: delivery.lastError,
      });
    }
  }

  private buildUserActionRecords(
    communityRef: string,
    userRef: string,
    moderationCaseId: string,
    events: UserActionEvent[],
    createdAt: Date
  ): UserActionRecord[] {
    const records: UserActionRecord[] = [];
    for (const event of events) {
      for (const action of event.actions) {
        records.push({
          communityRef,
          userRef,
          action,
          riskClass: event.class,
          severity: event.severity,
          moderationCaseId,
          createdAt,
        });
      }
    }
    return records;
  }
}