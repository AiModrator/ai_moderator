/**
 * DecisionProcessor — cœur métier : transforme un `DecisionJob` en `Verdict`.
 * Pure orchestration (décision) : pas de persistance ni de callback ici
 * (ajoutés dans la tâche 07). Logique/§5 de `main.md`.
 */

import type { ContentAction, UserAction } from '@ai-moderator/database';
import type { DecisionJob } from '../types/job.js';
import type { Verdict, VerdictDetection } from '../types/verdict.js';
import { moderationCaseId } from '../utils/id.js';
import type { CommunityRepository } from '../models/communityRepository.js';
import type { RuleRepository } from '../models/ruleRepository.js';
import type { ThresholdRepository } from '../models/thresholdRepository.js';
import type { SeverityResolver } from './severityResolver.js';
import type { ActionResolver } from './actionResolver.js';
import type { Logger } from '../utils/logger.js';

export interface DecisionProcessorContext {
  communityRepository: CommunityRepository;
  ruleRepository: RuleRepository;
  thresholdRepository: ThresholdRepository;
  severityResolver: SeverityResolver;
  actionResolver: ActionResolver;
  logger: Logger;
}

export class DecisionProcessor {
  constructor(private readonly ctx: DecisionProcessorContext) {}

  async process(job: DecisionJob): Promise<Verdict> {
    const logger = this.ctx.logger.child({ jobId: `${job.batchId}:${job.content.contentId}` });

    // 1. Contexte communautaire (CommunityNotFoundError propagée en cas d'absence).
    const community = await this.ctx.communityRepository.findByRef(job.communityRef);
    logger.debug('config.loaded', { workflowId: community.workflowId });

    // 2. Règles + seuils du workflow.
    const rules = community.workflowId ? await this.ctx.ruleRepository.findByWorkflow(community.workflowId) : [];
    const thresholds = community.workflowId ? await this.ctx.thresholdRepository.findByWorkflow(community.workflowId) : [];

    // 3. Boucle détections → sévérité → actions. Seules les sévérités
    //    non-NONE sont retenues dans le verdict (et déclenchent des actions).
    const detections: VerdictDetection[] = [];
    const contentActions = new Set<ContentAction>();
    const userActions = new Set<UserAction>();

    for (const detection of job.detections) {
      const threshold = this.ctx.thresholdRepository.resolve(detection.class, thresholds);
      const severity = this.ctx.severityResolver.resolve(detection.score, threshold);

      logger.debug('severity.resolved', { class: detection.class, score: detection.score, severity });

      if (severity === 'NONE') continue;

      const actions = this.ctx.actionResolver.resolve(detection.class, severity, rules);
      logger.debug('actions.resolved', {
        class: detection.class,
        severity,
        contentActions: actions.contentActions,
        userActions: actions.userActions,
      });

      detections.push({ class: detection.class, score: detection.score, severity, sources: detection.sources });
      for (const action of actions.contentActions) contentActions.add(action);
      for (const action of actions.userActions) userActions.add(action);
    }

    // 4. Révision humaine (job PARTIAL) — décision D4.
    let status: Verdict['status'] = 'completed';
    let needsReview = false;
    if (job.status === 'PARTIAL') {
      status = 'pending_review';
      needsReview = true;
      contentActions.add('FLAG_FOR_REVIEW');
    }

    // 5. Décision + idempotence (uuid v5 déterministe).
    const decision: Verdict['decision'] = contentActions.size > 0 || userActions.size > 0 ? 'action_taken' : 'allow';

    return {
      moderationCaseId: moderationCaseId(job.batchId, job.content.contentId),
      contentId: job.content.contentId,
      communityRef: job.communityRef,
      userRef: job.content.userRef,
      contentType: job.content.contentType,
      status,
      decision,
      detections,
      contentActions: [...contentActions],
      userActions: [...userActions],
      needsReview,
    };
  }
}