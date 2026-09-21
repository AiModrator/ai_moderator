/**
 * Tâche 10 — ThrottlingService (réservation de tokens, attente de refill).
 * Tests d'intégration : Redis réel.
 */

import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { randomUUID } from 'node:crypto';
import { RedisClient } from '../../src/core/RedisClient.js';
import { RedisService } from '../../src/core/RedisService.js';
import { ThrottlingService } from '../../src/core/ThrottlingService.js';
import { StdoutMetricsProvider } from '../../src/core/metrics/StdoutMetricsProvider.js';
import { Logger } from '../../src/config/logger.js';
import { testRedisHost, testRedisPort, flushRedis } from '../utils/redis.js';

describe('ThrottlingService', { tags: ['integration'] }, () => {
  let redisClient: RedisClient;
  let redisService: RedisService;
  const logger = new Logger('error');

  beforeAll(async () => {
    redisClient = new RedisClient(testRedisHost(), testRedisPort());
    redisService = new RedisService(redisClient);
    await redisClient.ping();
    await flushRedis();
  });

  afterAll(async () => {
    await redisClient.disconnect();
  });

  function buildService(config: {
    capacity: number;
    costPerToken: number;
    refillIntervalMs: number;
  }): { service: ThrottlingService; metrics: StdoutMetricsProvider } {
    const metrics = new StdoutMetricsProvider(() => undefined);
    const service = new ThrottlingService(redisService, metrics, config, logger);
    return { service, metrics };
  }

  it('ne réserve jamais plus que demandé (costPerToken > 1)', async () => {
    await redisService.resetBucket('global', { capacity: 100 });
    const { service } = buildService({ capacity: 100, costPerToken: 2, refillIntervalMs: 60000 });

    const awarded = await service.reserve(`c-${randomUUID()}`, 3);

    expect(awarded).toBe(3);
  });

  it('requête <= 0 → 0 sans consommer', async () => {
    await redisService.resetBucket('global', { capacity: 100 });
    const { service } = buildService({ capacity: 100, costPerToken: 1, refillIntervalMs: 60000 });

    await expect(service.reserve('community-x', 0)).resolves.toBe(0);
  });

  it('bucket vide → attend le prochain refill puis accorde tout', async () => {
    await redisService.resetBucket('global', { capacity: 1 });
    const { service } = buildService({ capacity: 1, costPerToken: 1, refillIntervalMs: 200 });

    const started = Date.now();
    const awarded = await service.reserve(`c-${randomUUID()}`, 2);
    const elapsed = Date.now() - started;

    expect(awarded).toBe(2);
    expect(elapsed).toBeGreaterThanOrEqual(100);
  });

  it('enregistre la métrique avec le tag communityRef', async () => {
    await redisService.resetBucket('global', { capacity: 100 });
    const { service, metrics } = buildService({
      capacity: 100,
      costPerToken: 1,
      refillIntervalMs: 60000,
    });
    const spy = vi.spyOn(metrics, 'record');

    const ref = `c-${randomUUID()}`;
    await service.reserve(ref, 1);

    expect(spy).toHaveBeenCalledWith('ingestion.throttle.tokens', 1, { communityRef: ref });
    spy.mockRestore();
  });

  it('réservations concurrentes ne dépassent jamais la capacité globale', async () => {
    const capacity = 60;
    await redisService.resetBucket('global', { capacity });
    const { service } = buildService({ capacity, costPerToken: 1, refillIntervalMs: 60000 });

    const [a, b] = await Promise.all([
      service.reserve('community-a', 30),
      service.reserve('community-b', 30),
    ]);

    expect(a + b).toBeLessThanOrEqual(capacity);
    expect(a + b).toBe(capacity);
  });
});