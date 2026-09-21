/**
 * Tâche 12 — IngestionController (orchestration du cycle webhook).
 * Tests d'intégration : Redis + Postgres + BullMQ réels, throttling simulé
 * pour rendre le comportement asynchrone déterministe.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from 'vitest';
import { randomUUID } from 'node:crypto';
import { RiskClass, Severity } from '@ai-moderator/database';
import { IngestionController } from '../../src/controllers/IngestionController.js';
import { AuthManager } from '../../src/core/AuthManager.js';
import { RedisClient } from '../../src/core/RedisClient.js';
import { RedisService } from '../../src/core/RedisService.js';
import { BullMQClient } from '../../src/core/BullMQClient.js';
import { DataDispatcher } from '../../src/core/DataDispatcher.js';
import { ThrottlingService } from '../../src/core/ThrottlingService.js';
import { Validator } from '../../src/core/Validator.js';
import { StdoutMetricsProvider } from '../../src/core/metrics/StdoutMetricsProvider.js';
import { ApiKeyRepository } from '../../src/repositories/ApiKeyRepository.js';
import { WorkflowRepository } from '../../src/repositories/WorkflowRepository.js';
import { Logger } from '../../src/config/logger.js';
import type { IncomingContent } from '../../src/types/payload.js';
import { testRedisHost, testRedisPort, flushRedis } from '../utils/redis.js';
import { resetDatabase, disconnectDatabase, seedCommunity } from '../utils/database.js';
import { getWaitingJobsCount, waitForJobs, clearQueue } from '../utils/queue.js';
import { makeItem } from '../utils/payload.js';

const SECRET = 'test-hmac-secret';

class SlowThrottle extends ThrottlingService {
  async reserve(communityRef: string, requested: number): Promise<number> {
    await new Promise((resolve) => setTimeout(resolve, 250));
    return super.reserve(communityRef, requested);
  }
}

class ChunkedThrottle extends ThrottlingService {
  readonly calls: number[] = [];
  async reserve(_communityRef: string, requested: number): Promise<number> {
    this.calls.push(Date.now());
    await new Promise((resolve) => setTimeout(resolve, 60));
    return Math.min(requested, 2);
  }
}

describe('IngestionController', { tags: ['integration'] }, () => {
  const queueName = `test-ingestion-${randomUUID()}`;
  let redisClient: RedisClient;
  let redisService: RedisService;
  let bullMQClient: BullMQClient;
  let dispatcher: DataDispatcher;
  let authManager: AuthManager;
  let workflowRepository: WorkflowRepository;
  let metrics: StdoutMetricsProvider;
  const logger = new Logger('error');

  beforeAll(async () => {
    redisClient = new RedisClient(testRedisHost(), testRedisPort());
    redisService = new RedisService(redisClient);
    bullMQClient = new BullMQClient({ host: testRedisHost(), port: testRedisPort() });
    dispatcher = new DataDispatcher(bullMQClient, queueName, logger);
    authManager = new AuthManager(new ApiKeyRepository(), redisService, SECRET, 60, logger);
    workflowRepository = new WorkflowRepository();
    metrics = new StdoutMetricsProvider(() => undefined);
    await redisClient.ping();
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await clearQueue(queueName);
    for (const queue of bullMQClient.getQueues().values()) {
      await queue.close();
    }
    await redisClient.disconnect();
    await disconnectDatabase();
  });

  beforeEach(async () => {
    await flushRedis();
    await clearQueue(queueName);
  });

  function buildController(overrides: {
    throttlingService?: ThrottlingService;
    backlogMaxPostsPerCommunity?: number;
  } = {}): IngestionController {
    const throttlingService =
      overrides.throttlingService ??
      new ThrottlingService(
        redisService,
        metrics,
        { capacity: 1000, costPerToken: 1, refillIntervalMs: 60000 },
        logger
      );

    return new IngestionController({
      validator: new Validator({ maxItemsPerBatch: 10 }),
      authManager,
      workflowRepository,
      throttlingService,
      dataDispatcher: dispatcher,
      redisService,
      logger,
      cacheConfigTtlSeconds: 60,
      backlogMaxPostsPerCommunity: overrides.backlogMaxPostsPerCommunity ?? 1000,
      backlogTtlSeconds: 60,
    });
  }

  it('payload valide → 202 immédiat, job dispatché en arrière-plan', async () => {
    const seed = await seedCommunity(SECRET, {
      rules: [
        { riskClass: RiskClass.SPAM, severity: Severity.LOW },
        { riskClass: RiskClass.TOXICITY, severity: Severity.HIGH },
      ],
    });
    const controller = buildController({ throttlingService: new SlowThrottle(redisService, metrics, { capacity: 1000, costPerToken: 1, refillIntervalMs: 60000 }, logger) });

    const response = await controller.handleWebhook({
      apiKey: seed.apiKeyRaw,
      body: { items: [makeItem({ contentId: 'a' })] },
    });

    expect(response.status).toBe(202);
    expect(response.body.status).toBe('accepted');
    expect(response.body.itemCount).toBe(1);
    expect(typeof response.body.acceptedId).toBe('string');

    // La réponse est rendue AVANT que le job n'existe (throttling différé).
    expect(await getWaitingJobsCount(queueName)).toBe(0);

    const jobs = await waitForJobs(queueName, 1, 5000);
    const payload = jobs[0].data as { communityRef: string; activeClasses: RiskClass[] };
    expect(payload.communityRef).toBe(seed.communityId);
    expect(new Set(payload.activeClasses)).toEqual(new Set([RiskClass.SPAM, RiskClass.TOXICITY]));
  });

  it('payload invalide → 400 sans authentifier ni throttle', async () => {
    const authSpy = vi.spyOn(authManager, 'authenticate');
    const throttle = new SlowThrottle(redisService, metrics, { capacity: 1000, costPerToken: 1, refillIntervalMs: 60000 }, logger);
    const reserveSpy = vi.spyOn(throttle, 'reserve');
    const controller = buildController({ throttlingService: throttle });

    const response = await controller.handleWebhook({
      apiKey: 'irrelevant',
      body: { items: [] },
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('validation_failed');
    expect(response.body.fields).toContain('items');
    expect(authSpy).not.toHaveBeenCalled();
    expect(reserveSpy).not.toHaveBeenCalled();
    expect(await getWaitingJobsCount(queueName)).toBe(0);

    authSpy.mockRestore();
    reserveSpy.mockRestore();
  });

  it('clé API invalide → 401, aucun job dispatché', async () => {
    const controller = buildController();

    const response = await controller.handleWebhook({
      apiKey: 'unknown-key',
      body: { items: [makeItem()] },
    });

    expect(response.status).toBe(401);
    expect(response.body.error).toBe('authentication_failed');
    expect(await getWaitingJobsCount(queueName)).toBe(0);
  });

  it('dépassement du backlog → 429, aucun job dispatché', async () => {
    const seed = await seedCommunity(SECRET);
    const controller = buildController({ backlogMaxPostsPerCommunity: 2 });

    const response = await controller.handleWebhook({
      apiKey: seed.apiKeyRaw,
      body: { items: [makeItem({ contentId: 'a' }), makeItem({ contentId: 'b' }), makeItem({ contentId: 'c' })] },
    });

    expect(response.status).toBe(429);
    expect(response.body.error).toBe('backlog_exceeded');
    expect(await getWaitingJobsCount(queueName)).toBe(0);
  });

  it('lot plus grand que les tokens → dispatches échelonnés dans le temps', async () => {
    const seed = await seedCommunity(SECRET);
    const throttle = new ChunkedThrottle(redisService, metrics, { capacity: 1000, costPerToken: 1, refillIntervalMs: 60000 }, logger);
    const controller = buildController({ throttlingService: throttle });
    const dispatchSpy = vi.spyOn(dispatcher, 'dispatchData');

    const items: IncomingContent[] = Array.from({ length: 5 }, (_, i) =>
      makeItem({ contentId: `c-${i}` })
    );

    const response = await controller.handleWebhook({ apiKey: seed.apiKeyRaw, body: { items } });
    expect(response.status).toBe(202);

    await waitForJobs(queueName, 3, 5000);

    expect(throttle.calls).toHaveLength(3);
    const dispatchedCounts = dispatchSpy.mock.calls.map((call) => call[0].length);
    expect(dispatchedCounts.reduce((sum, n) => sum + n, 0)).toBe(5);
    const span = throttle.calls[throttle.calls.length - 1] - throttle.calls[0];
    expect(span).toBeGreaterThanOrEqual(100);

    dispatchSpy.mockRestore();
  });
});