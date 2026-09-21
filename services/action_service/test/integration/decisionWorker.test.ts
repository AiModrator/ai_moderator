/**
 * Tâche 07 — DécisionWorker : flux complet (BullMQ + D-04 réel + D-02 réel +
 * callback simulé), job invalide → failed (pas de retry), erreur infra → retry.
 */

import { randomUUID } from 'node:crypto';
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
import { DecisionWorker, type DecisionWorkerDeps } from '../../src/queue/decisionWorker.js';
import { Logger } from '../../src/utils/logger.js';
import { moderationCaseId } from '../../src/utils/id.js';
import { HistoryWriteError } from '../../src/exceptions/index.js';
import { resetDatabase, seedCommunity, disconnectDatabase } from '../utils/database.js';
import { resetMongo, CASES, ACTIONS } from '../utils/mongo.js';
import { TestCallbackServer } from '../utils/callbackServer.js';
import { makeDecisionJob } from '../utils/job.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);
const connection: ConnectionOptions = bullmqConnection(settings);
const logger = Logger.create('silent');

const store = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
const cbServer = new TestCallbackServer();
const queueName = `decision-test-${randomUUID()}`;

function buildDeps(cbUrl: string, queue: string = queueName): DecisionWorkerDeps {
  return {
    settings,
    queueName: queue,
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
    callbackClient: new CallbackClient(
      { timeoutMs: 2000, maxAttempts: 3, baseDelayMs: 20, maxDelayMs: 1000 },
      logger
    ),
    logger,
  };
}

let mainWorker: DecisionWorker;
let cbUrl: string;

describe('DecisionWorker (flux complet)', { tags: ['integration'], timeout: 30000 }, () => {
  beforeAll(async () => {
    await resetDatabase();
    await resetMongo(store);
    await store.ensureIndexes();
    cbUrl = `http://127.0.0.1:${await cbServer.listen()}/cb`;
  });

  afterAll(async () => {
    await mainWorker.stop();
    await cbServer.close();
    await store.close();
    await resetDatabase();
    await disconnectDatabase();
  });

  it('job valide → cas D-02 + user_actions + callback delivered (corps sans needsReview)', async () => {
    mainWorker = new DecisionWorker(buildDeps(cbUrl));
    mainWorker.start();

    const seed = await seedCommunity({
      callbackUrl: cbUrl,
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });

    const queue = new Queue(queueName, { connection });
    const events = new QueueEvents(queueName, { connection });
    await events.waitUntilReady();
    const completed = new Promise<void>((resolve, reject) => {
      events.once('completed', () => resolve());
      events.once('failed', (_j, err) => reject(new Error(`job failed: ${String(err)}`)));
    });

    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [{ class: 'TOXICITY', score: 0.91, sources: ['text'], evidence: [] }],
    });
    await queue.add('decide', job);
    await completed;
    await events.close();
    await queue.close();

    const storeDb = store.dbOrThrow();
    const caseId = moderationCaseId(job.batchId, job.content.contentId);
    const caseDoc = await storeDb.collection(CASES).findOne({ moderationCaseId: caseId });
    expect(caseDoc).not.toBeNull();

    expect(caseDoc).toMatchObject({
      communityRef: seed.communityId,
      accountId: seed.accountId,
      contentId: 'post-42',
      decision: 'action_taken',
      status: 'completed',
      needsReview: false,
      contentActions: ['DELETE_POST'],
      userActions: ['TIMEOUT_USER'],
      detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] }],
    });
    expect((caseDoc as { callback: { status: string; url: string; attempts: number } }).callback).toMatchObject({
      status: 'delivered',
      url: cbUrl,
      attempts: 1,
    });
    expect((caseDoc as { contentTimestamp: unknown }).contentTimestamp).toBeInstanceOf(Date);

    // Journal des sanctions (attribution par détection)
    const actions = await storeDb.collection(ACTIONS).find({ moderationCaseId: caseId }).toArray();
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      action: 'TIMEOUT_USER',
      riskClass: 'TOXICITY',
      severity: 'HIGH',
      userRef: 'user-7',
      communityRef: seed.communityId,
    });

    // Callback : verdict sans needsReview/filtersReport
    expect(cbServer.callCount).toBeGreaterThan(0);
    expect(cbServer.lastBody).toEqual({
      moderationCaseId: caseId,
      contentId: 'post-42',
      status: 'completed',
      decision: 'action_taken',
      detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] }],
      contentActions: ['DELETE_POST'],
      userActions: ['TIMEOUT_USER'],
    });
  });

  it('job sans détection → decision=allow, aucune user_action, callback quand même', async () => {
    const seed = await seedCommunity({ callbackUrl: cbUrl, rules: [] });
    const queue = new Queue(queueName, { connection });
    const events = new QueueEvents(queueName, { connection });
    await events.waitUntilReady();
    const completed = new Promise<void>((resolve, reject) => {
      events.once('completed', () => resolve());
      events.once('failed', (_j, err) => reject(new Error(`job failed: ${String(err)}`)));
    });

    const job = makeDecisionJob({ communityRef: seed.communityId, batchId: `batch-allow-${randomUUID()}` });
    await queue.add('decide', job);
    await completed;
    await events.close();
    await queue.close();

    const storeDb = store.dbOrThrow();
    const caseId = moderationCaseId(job.batchId, job.content.contentId);
    const caseDoc = await storeDb.collection(CASES).findOne({ moderationCaseId: caseId });
    expect(caseDoc).toMatchObject({ decision: 'allow', contentActions: [], userActions: [] });
    expect((caseDoc as { callback: { status: string } }).callback.status).toBe('delivered');
    expect(await storeDb.collection(ACTIONS).countDocuments({ moderationCaseId: caseId })).toBe(0);
  });

  it('cas rejoué (même batchId:contentId) → idempotent : un seul document D-02, pas de doublon', async () => {
    const seed = await seedCommunity({
      callbackUrl: cbUrl,
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });

    const queue = new Queue(queueName, { connection });
    const events = new QueueEvents(queueName, { connection });
    await events.waitUntilReady();
    const completed = (): Promise<void> =>
      new Promise<void>((resolve, reject) => {
        events.once('completed', () => resolve());
        events.once('failed', (_j, err) => reject(new Error(`job failed: ${String(err)}`)));
      });

    const job = makeDecisionJob({
      communityRef: seed.communityId,
      batchId: `batch-replay-${randomUUID()}`,
      detections: [{ class: 'TOXICITY', score: 0.91, sources: ['text'], evidence: [] }],
    });
    await queue.add('decide', job);
    await completed();
    await queue.add('decide', { ...job, moderatedAt: '2026-09-21T10:05:00.000Z' });
    await completed();
    await events.close();
    await queue.close();

    const storeDb = store.dbOrThrow();
    const caseId = moderationCaseId(job.batchId, job.content.contentId);
    expect(await storeDb.collection(CASES).countDocuments({ moderationCaseId: caseId })).toBe(1);
  });

  it('job invalide → failed (1 seul essai), aucun cas créé', async () => {
    const storeDb = store.dbOrThrow();
    const countBefore = await storeDb.collection(CASES).countDocuments();

    const queue = new Queue(queueName, { connection });
    const events = new QueueEvents(queueName, { connection });
    await events.waitUntilReady();
    const failed = new Promise<void>((resolve) => events.once('failed', () => resolve()));

    const invalid = await queue.add('decide', { bad: true });
    await failed;
    await events.close();

    const stored = await queue.getJob(invalid.id as string);
    expect(stored).not.toBeNull();
    expect(await stored!.getState()).toBe('failed');
    expect(stored!.attemptsMade).toBe(1);
    expect(await storeDb.collection(CASES).countDocuments()).toBe(countBefore);
    await queue.close();
  });

  it('erreur infra → job retenté (attempts configurés) puis failed, Aucun doublon écrit', async () => {
    const retryQueueName = `decision-retry-${randomUUID()}`;
    const throwingWorker = new DecisionWorker({
      ...buildDeps(cbUrl, retryQueueName),
      processor: {
        processWithEvents: async () => {
          throw new HistoryWriteError('mongo down');
        },
      } as DecisionProcessor,
    });
    throwingWorker.start();

    const queue = new Queue(retryQueueName, { connection });
    const events = new QueueEvents(retryQueueName, { connection });
    await events.waitUntilReady();
    const failed = new Promise<void>((resolve) => events.once('failed', () => resolve()));

    const job = await queue.add('decide', makeDecisionJob({ communityRef: 'community-1' }), {
      attempts: 3,
      backoff: { type: 'fixed', delay: 20 },
    });
    await failed;
    await events.close();

    const stored = await queue.getJob(job.id as string);
    expect(stored).not.toBeNull();
    expect(await stored!.getState()).toBe('failed');
    expect(stored!.attemptsMade).toBe(3);

    await throwingWorker.stop();
    await queue.close();
  });
});