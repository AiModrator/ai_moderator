/**
 * Tâche 08 — E2E : queue → décision (seuils/calibration personnalisés) →
 * D-02 (cas + user_actions) → callback → `GET /cases/:id` (filet §7.2).
 * Variante PARTIAL → pending_review + needsReview visibles via l'API.
 */

import { randomUUID } from 'node:crypto';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Queue, QueueEvents, type ConnectionOptions } from 'bullmq';
import { ContentAction, Severity, UserAction } from '@ai-moderator/database';
import { Settings } from '../../src/config/settings.js';
import { bullmqConnection } from '../../src/config/redis.js';
import { MongoStore } from '../../src/config/mongo.js';
import { CommunityRepository } from '../../src/models/communityRepository.js';
import { RuleRepository } from '../../src/models/ruleRepository.js';
import { ThresholdRepository } from '../../src/models/thresholdRepository.js';
import { ModerationCaseRepository } from '../../src/models/moderationCaseRepository.js';
import { UserActionRepository } from '../../src/models/userActionRepository.js';
import { SeverityResolver } from '../../src/service/severityResolver.js';
import { ActionResolver } from '../../src/service/actionResolver.js';
import { DecisionProcessor } from '../../src/service/decisionProcessor.js';
import { CallbackClient } from '../../src/service/callbackClient.js';
import { DecisionWorker } from '../../src/queue/decisionWorker.js';
import { CaseController } from '../../src/controllers/caseController.js';
import { createApp } from '../../src/app.js';
import { Logger } from '../../src/utils/logger.js';
import { resetDatabase, seedCommunity, disconnectDatabase } from '../utils/database.js';
import { resetMongo, CASES } from '../utils/mongo.js';
import { TestCallbackServer } from '../utils/callbackServer.js';
import { makeDecisionJob } from '../utils/job.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);
const connection: ConnectionOptions = bullmqConnection(settings);
const logger = Logger.create('silent');

const queueName = `decision-e2e-${randomUUID()}`;
const store = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
const cbServer = new TestCallbackServer();

function buildDeps(cbUrl: string) {
  return {
    settings,
    queueName,
    communityRepository: new CommunityRepository(logger),
    processor: new DecisionProcessor({
      communityRepository: new CommunityRepository(logger),
      ruleRepository: new RuleRepository(logger),
      thresholdRepository: new ThresholdRepository(logger),
      severityResolver: new SeverityResolver(),
      actionResolver: new ActionResolver(),
      logger,
    }),
    caseRepository: new ModerationCaseRepository(store, logger),
    userActionRepository: new UserActionRepository(store, logger),
    callbackClient: new CallbackClient({ timeoutMs: 2000, maxAttempts: 3, baseDelayMs: 20, maxDelayMs: 1000 }, logger),
    logger,
  };
}

let worker: DecisionWorker;
let app: ReturnType<typeof createApp>;
let cbUrl: string;

describe('E2E — flux complet du service', { tags: ['e2e'], timeout: 30000 }, () => {
  beforeAll(async () => {
    await resetDatabase();
    await store.connect();
    await resetMongo(store);
    await store.ensureIndexes();
    cbUrl = `http://127.0.0.1:${await cbServer.listen()}/cb`;

    worker = new DecisionWorker(buildDeps(cbUrl));
    worker.start();

    const caseApi = new CaseController(new ModerationCaseRepository(store, logger), logger);
    app = createApp({ routers: [caseApi.router()] });
  });

  afterAll(async () => {
    await worker.stop();
    await cbServer.close();
    await store.close();
    await resetDatabase();
    await disconnectDatabase();
  });

  async function runJob(job: unknown): Promise<void> {
    const queue = new Queue(queueName, { connection });
    const events = new QueueEvents(queueName, { connection });
    await events.waitUntilReady();
    const done = new Promise<void>((resolve, reject) => {
      events.once('completed', () => resolve());
      events.once('failed', (_j, err) => reject(new Error(`job failed: ${String(err)}`)));
    });
    await queue.add('decide', job);
    await done;
    await events.close();
    await queue.close();
  }

  it('décision par calibration personnalisée (critical=0.90 → CRITICAL → BAN_USER) + callback + GET case', async () => {
    const seed = await seedCommunity({
      callbackUrl: cbUrl,
      thresholds: [{ riskClass: 'TOXICITY', low: 0.25, medium: 0.5, high: 0.75, critical: 0.9 }],
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.CRITICAL, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.BAN_USER] },
      ],
    });

    const job = makeDecisionJob({
      communityRef: seed.communityId,
      batchId: `e2e-cal-${randomUUID()}`,
      detections: [{ class: 'TOXICITY', score: 0.95, sources: ['text', 'image'], evidence: [] }],
    });
    await runJob(job);

    // Cas persisté en D-02
    const storeDb = store.dbOrThrow();
    const caseId = (await storeDb.collection(CASES).findOne({ contentId: 'post-42' })) as {
      moderationCaseId: string;
      decision: string;
      contentActions: string[];
      userActions: string[];
      needsReview: boolean;
      detections: Array<{ class: string; score: number; severity: string }>;
      callback: { status: string };
    } | null;
    expect(caseId).not.toBeNull();

    const abs = caseId as NonNullable<typeof caseId>;
    expect(abs).toMatchObject({
      decision: 'action_taken',
      contentActions: ['DELETE_POST'],
      userActions: ['BAN_USER'],
      needsReview: false,
    });
    expect(abs.detections).toEqual([{ class: 'TOXICITY', score: 0.95, severity: 'CRITICAL', sources: ['text', 'image'] }]);
    expect(abs.callback.status).toBe('delivered');

    // Filet de sécurité : lecture via HTTP
    const res = await request(app).get(`/cases/${abs.moderationCaseId}`).expect(200);
    expect(res.body).toMatchObject({
      moderationCaseId: abs.moderationCaseId,
      decision: 'action_taken',
      contentActions: ['DELETE_POST'],
      userActions: ['BAN_USER'],
      status: 'completed',
    });
    expect(res.body['needsReview']).toBe(false);

    // Sanction journalisée avec attribution de la détection
    const actions = await storeDb.collection('user_actions').find({ moderationCaseId: abs.moderationCaseId }).toArray();
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ action: 'BAN_USER', riskClass: 'TOXICITY', severity: 'CRITICAL', userRef: 'user-7' });

    // Callback reçu : sources tableau + score (évolutions rétro-compatibles §7.1)
    expect(cbServer.lastBody).toMatchObject({
      moderationCaseId: abs.moderationCaseId,
      detections: [{ class: 'TOXICITY', score: 0.95, severity: 'CRITICAL', sources: ['text', 'image'] }],
      userActions: ['BAN_USER'],
    });
  });

  it('PARTIAL → pending_review + needsReview via GET /cases/:id + FLAG_FOR_REVIEW', async () => {
    const seed = await seedCommunity({
      callbackUrl: cbUrl,
      thresholds: [{ riskClass: 'TOXICITY', low: 0.25 }],
      rules: [{ riskClass: 'TOXICITY', severity: Severity.MEDIUM, contentActions: [ContentAction.HIDE_POST], userActions: [UserAction.WARN_USER] }],
    });

    const job = makeDecisionJob({
      communityRef: seed.communityId,
      batchId: `e2e-partial-${randomUUID()}`,
      status: 'PARTIAL',
      filtersReport: [
        { filter: 'TextAIFilter', status: 'UNAVAILABLE', attempts: 1, error: 'provider rate limited' },
        { filter: 'SpamFilter', status: 'COMPLETED', attempts: 1, error: null },
      ],
      detections: [{ class: 'TOXICITY', score: 0.6, sources: ['text'], evidence: [] }],
    });
    await runJob(job);

    const storeDb = store.dbOrThrow();
    const cas = (await storeDb.collection(CASES).findOne({ contentId: 'post-42', needsReview: true })) as {
      moderationCaseId: string;
      status: string;
      needsReview: boolean;
      contentActions: string[];
    } | null;
    expect(cas).not.toBeNull();
    const abs = cas as NonNullable<typeof cas>;
    expect(abs.status).toBe('pending_review');
    expect(abs.needsReview).toBe(true);
    expect(abs.contentActions).toEqual(['HIDE_POST', 'FLAG_FOR_REVIEW']);

    const res = await request(app).get(`/cases/${abs.moderationCaseId}`).expect(200);
    expect(res.body).toMatchObject({ status: 'pending_review', needsReview: true });
  });

  it('GET /cases/inconnu → 404', async () => {
    await request(app).get('/cases/absent').expect(404);
  });
});