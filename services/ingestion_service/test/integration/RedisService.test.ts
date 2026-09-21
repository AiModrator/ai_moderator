/**
 * Tâche 05 — RedisService (cache-aside + bucket de tokens + backlog).
 * Tests d'intégration : Redis réel.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { randomUUID } from 'node:crypto';
import { RedisClient } from '../../src/core/RedisClient.js';
import { RedisService } from '../../src/core/RedisService.js';
import { testRedisHost, testRedisPort, flushRedis } from '../utils/redis.js';

describe('RedisService', { tags: ['integration'] }, () => {
  let redisClient: RedisClient;
  let redisService: RedisService;

  beforeAll(async () => {
    redisClient = new RedisClient(testRedisHost(), testRedisPort());
    redisService = new RedisService(redisClient);
    await redisClient.ping();
    await flushRedis();
  });

  afterAll(async () => {
    await redisClient.disconnect();
  });

  describe('getOrSet (cache-aside)', () => {
    it('cache miss → appelle le fallback et retourne sa valeur', async () => {
      const key = `test:cache:${randomUUID()}`;
      let calls = 0;
      const fallback = async (): Promise<{ n: number }> => {
        calls += 1;
        return { n: 42 };
      };

      const value = await redisService.getOrSet(key, fallback, 60);

      expect(value).toEqual({ n: 42 });
      expect(calls).toBe(1);
    });

    it('cache hit → ne rappelle pas le fallback', async () => {
      const key = `test:cache:${randomUUID()}`;
      let calls = 0;
      const fallback = async (): Promise<number> => {
        calls += 1;
        return calls;
      };

      await redisService.getOrSet(key, fallback, 60);
      const second = await redisService.getOrSet(key, fallback, 60);

      expect(second).toBe(1);
      expect(calls).toBe(1);
    });

    it('après expiration du TTL → le fallback est rappelé', async () => {
      const key = `test:cache:${randomUUID()}`;
      let calls = 0;
      const fallback = async (): Promise<number> => {
        calls += 1;
        return calls;
      };

      await redisService.getOrSet(key, fallback, 1);
      await new Promise((resolve) => setTimeout(resolve, 1100));
      const refreshed = await redisService.getOrSet(key, fallback, 1);

      expect(refreshed).toBe(2);
      expect(calls).toBe(2);
    });
  });

  describe('consumeBucket (bucket de tokens)', () => {
    it('retourne exactement le nombre demandé quand assez de tokens', async () => {
      const key = `b-${randomUUID()}`;
      await redisService.resetBucket(key, { capacity: 10 });

      const granted = await redisService.consumeBucket(key, {
        capacity: 10,
        costPerToken: 1,
        refillIntervalMs: 60000,
        requested: 3,
      });

      expect(granted).toBe(3);
    });

    it("ne retourne jamais plus que demandé", async () => {
      const key = `b-${randomUUID()}`;
      await redisService.resetBucket(key, { capacity: 10 });

      const granted = await redisService.consumeBucket(key, {
        capacity: 10,
        costPerToken: 1,
        refillIntervalMs: 60000,
        requested: 100,
      });

      expect(granted).toBe(10);
    });

    it('consommations concurrentes ne dépassent jamais la capacité', async () => {
      const key = `b-${randomUUID()}`;
      const capacity = 5;
      await redisService.resetBucket(key, { capacity });

      const results = await Promise.all(
        Array.from({ length: 5 }, () =>
          redisService.consumeBucket(key, {
            capacity,
            costPerToken: 1,
            refillIntervalMs: 60000,
            requested: 2,
          })
        )
      );

      const total = results.reduce((sum, n) => sum + n, 0);
      expect(total).toBeLessThanOrEqual(capacity);
      expect(total).toBe(capacity);
    });

    it('requête <= 0 retourne 0 sans consommer', async () => {
      const key = `b-${randomUUID()}`;
      await redisService.resetBucket(key, { capacity: 5 });
      const granted = await redisService.consumeBucket(key, {
        capacity: 5,
        costPerToken: 1,
        refillIntervalMs: 60000,
        requested: 0,
      });
      expect(granted).toBe(0);
    });
  });

  describe('backlog', () => {
    it('incrémente et décrémente atomiquement, borné à 0', async () => {
      const ref = `c-${randomUUID()}`;
      await expect(redisService.changeBacklog(ref, 5, 60)).resolves.toBe(5);
      await expect(redisService.changeBacklog(ref, -3, 60)).resolves.toBe(2);
      await expect(redisService.changeBacklog(ref, -100, 60)).resolves.toBe(0);
      await expect(redisService.getBacklog(ref)).resolves.toBe(0);
    });

    it('resetBacklog remet le compteur à 0', async () => {
      const ref = `c-${randomUUID()}`;
      await redisService.changeBacklog(ref, 7, 60);
      await redisService.resetBacklog(ref);
      await expect(redisService.getBacklog(ref)).resolves.toBe(0);
    });
  });
});