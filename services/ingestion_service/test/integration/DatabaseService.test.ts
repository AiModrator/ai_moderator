/**
 * Tâche 02 — DatabaseService (client Prisma partagé).
 * Tests d'intégration : base Postgres D-04 réelle.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import databaseService, { DatabaseService } from '../../src/core/DatabaseService.js';
import { resetDatabase, disconnectDatabase } from '../utils/database.js';

describe('DatabaseService', { tags: ['integration'] }, () => {
  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await disconnectDatabase();
  });

  it('plusieurs instances partagent le même client Prisma (pool unique)', () => {
    const a = new DatabaseService();
    const b = new DatabaseService();
    expect(a.client).toBe(b.client);
    expect(a.client).toBe(databaseService.client);
  });

  it('checkConnection() résout quand la base est joignable', async () => {
    await expect(new DatabaseService().checkConnection()).resolves.toBeUndefined();
  });

  it('exécute une requête réelle via le client partagé', async () => {
    const count = await databaseService.client.account.count();
    expect(count).toBe(0);
  });
});