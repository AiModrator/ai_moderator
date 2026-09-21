/**
 * Tâche 06 — ApiKeyRepository (résolution clé API → Community).
 * Tests d'intégration : base Postgres D-04 réelle.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { ApiKeyRepository } from '../../src/repositories/ApiKeyRepository.js';
import { resetDatabase, disconnectDatabase, seedCommunity } from '../utils/database.js';

const SECRET = 'test-hmac-secret';

describe('ApiKeyRepository', { tags: ['integration'] }, () => {
  const repository = new ApiKeyRepository();

  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('clé existante non révoquée → retourne la bonne communauté', async () => {
    const seed = await seedCommunity(SECRET);
    const community = await repository.findByHash(seed.apiKeyHashed);

    expect(community).not.toBeNull();
    expect(community?.id).toBe(seed.communityId);
  });

  it('clé inconnue → retourne null (jamais d’exception)', async () => {
    await expect(repository.findByHash('unknown-hash')).resolves.toBeNull();
  });

  it('clé révoquée → retourne null', async () => {
    const seed = await seedCommunity(SECRET, { revoked: true });
    await expect(repository.findByHash(seed.apiKeyHashed)).resolves.toBeNull();
  });
});