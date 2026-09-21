/**
 * Tâche 01 — RedisClient (wrapper bas niveau ioredis).
 * Tests d'intégration : connexion Redis réelle ; un cas de connexion
 * injoignable est testé sans dépendre d'un serveur.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { RedisClient } from '../../src/core/RedisClient.js';
import { RedisError } from '../../src/types/errors.js';
import { testRedisHost, testRedisPort, flushRedis } from '../utils/redis.js';

describe('RedisClient', { tags: ['integration'] }, () => {
  let redis: RedisClient;

  beforeAll(async () => {
    redis = new RedisClient(testRedisHost(), testRedisPort());
    await redis.ping();
    await flushRedis();
  });

  afterAll(async () => {
    await redis.disconnect();
  });

  it('set puis get renvoie la même valeur', async () => {
    await redis.set('test:key', 'hello');
    await expect(redis.get('test:key')).resolves.toBe('hello');
  });

  it('get sur une clé absente renvoie null', async () => {
    await expect(redis.get('test:missing')).resolves.toBeNull();
  });

  it('set avec TTL expire la clé', async () => {
    await redis.set('test:ttl', 'v', 1);
    await expect(redis.get('test:ttl')).resolves.toBe('v');
    await new Promise((resolve) => setTimeout(resolve, 1100));
    await expect(redis.get('test:ttl')).resolves.toBeNull();
  });

  it('eval exécute un script Lua et retourne le résultat', async () => {
    const script = "redis.call('SET', KEYS[1], ARGV[1]); return redis.call('GET', KEYS[1])";
    await expect(redis.eval(script, ['test:lua'], ['42'])).resolves.toBe('42');
    await expect(redis.get('test:lua')).resolves.toBe('42');
  });

  it('ping renvoie PONG', async () => {
    await expect(redis.ping()).resolves.toBe('PONG');
  });

  it(
    'connexion injoignable → les commandes rejettent une RedisError typée',
    async () => {
      const broken = new RedisClient('127.0.0.1', 6399);
      await expect(broken.get('anything')).rejects.toBeInstanceOf(RedisError);
      await broken.disconnect();
    },
    15000
  );
});