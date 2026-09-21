/**
 * Tâche 09 — AuthManager (authentification + cache-aside).
 * Tests d'intégration : Redis + Postgres réels.
 */

import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import prisma from '@ai-moderator/database';
import { AuthManager } from '../../src/core/AuthManager.js';
import { RedisClient } from '../../src/core/RedisClient.js';
import { RedisService } from '../../src/core/RedisService.js';
import { ApiKeyRepository } from '../../src/repositories/ApiKeyRepository.js';
import { AuthenticationError } from '../../src/types/errors.js';
import { Logger } from '../../src/config/logger.js';
import { testRedisHost, testRedisPort, flushRedis } from '../utils/redis.js';
import { resetDatabase, disconnectDatabase, seedCommunity } from '../utils/database.js';

const SECRET = 'test-hmac-secret';

describe('AuthManager', { tags: ['integration'] }, () => {
  let redisClient: RedisClient;
  let repository: ApiKeyRepository;
  let authManager: AuthManager;

  beforeAll(async () => {
    redisClient = new RedisClient(testRedisHost(), testRedisPort());
    const redisService = new RedisService(redisClient);
    repository = new ApiKeyRepository();
    await redisClient.ping();
    await resetDatabase();
    await flushRedis();
  });

  afterAll(async () => {
    await resetDatabase();
    await redisClient.disconnect();
    await disconnectDatabase();
  });

  function buildManager(cacheTtlSeconds = 300): AuthManager {
    const redisService = new RedisService(redisClient);
    return new AuthManager(
      repository,
      redisService,
      SECRET,
      cacheTtlSeconds,
      new Logger('error')
    );
  }

  it('clé valide → retourne la communauté résolue', async () => {
    const seed = await seedCommunity(SECRET);
    const manager = buildManager();

    const community = await manager.authenticate(seed.apiKeyRaw);

    expect(community.id).toBe(seed.communityId);
  });

  it('clé absente → AuthenticationError', async () => {
    const manager = buildManager();
    await expect(manager.authenticate(undefined)).rejects.toBeInstanceOf(AuthenticationError);
    await expect(manager.authenticate('')).rejects.toBeInstanceOf(AuthenticationError);
  });

  it('clé inconnue → AuthenticationError', async () => {
    const manager = buildManager();
    await expect(manager.authenticate('unknown-key')).rejects.toBeInstanceOf(AuthenticationError);
  });

  it('second appel dans le TTL → pas de requête base (cache hit)', async () => {
    const seed = await seedCommunity(SECRET);
    const manager = buildManager(60);
    const spy = vi.spyOn(repository, 'findByHash');

    await manager.authenticate(seed.apiKeyRaw);
    expect(spy).toHaveBeenCalledTimes(1);

    await manager.authenticate(seed.apiKeyRaw);
    expect(spy).toHaveBeenCalledTimes(1);

    spy.mockRestore();
  });

  it('clé révoquée (jamais cachée) → AuthenticationError', async () => {
    const seed = await seedCommunity(SECRET, { revoked: true });
    const manager = buildManager();
    await expect(manager.authenticate(seed.apiKeyRaw)).rejects.toBeInstanceOf(AuthenticationError);
  });

  it('révocation observée après expiration du cache (cohérence à terme)', async () => {
    const seed = await seedCommunity(SECRET);
    const manager = buildManager(1);

    // 1er appel : communauté mise en cache.
    await expect(manager.authenticate(seed.apiKeyRaw)).resolves.toMatchObject({
      id: seed.communityId,
    });

    // Révocation en base : le cache reste valide jusqu'à expiration.
    await prisma.apiKey.updateMany({
      where: { communityId: seed.communityId },
      data: { revokedAt: new Date() },
    });

    // Immédiatement : encore servi par le cache (limite connue documentée).
    await expect(manager.authenticate(seed.apiKeyRaw)).resolves.toMatchObject({
      id: seed.communityId,
    });

    // Après expiration du TTL : la révocation est observée.
    await new Promise((resolve) => setTimeout(resolve, 1100));
    await expect(manager.authenticate(seed.apiKeyRaw)).rejects.toBeInstanceOf(AuthenticationError);
  });
});