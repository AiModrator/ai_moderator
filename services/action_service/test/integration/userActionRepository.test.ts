/**
 * Tâche 04 — UserActionRepository (D-02, Mongo réel).
 * Tests d'intégration : insertMany + index (communityRef, userRef, createdAt).
 */

import { beforeAll, afterAll, describe, it, expect } from 'vitest';
import { Settings } from '../../src/config/settings.js';
import { MongoStore } from '../../src/config/mongo.js';
import { UserActionRepository } from '../../src/models/userActionRepository.js';
import { Logger } from '../../src/utils/logger.js';
import { resetMongo, makeUserActionRecord, ACTIONS, countDocuments } from '../utils/mongo.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);
const store = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
const logger = Logger.create('silent');
const repo = new UserActionRepository(store, logger);

describe('UserActionRepository', { tags: ['integration'] }, () => {
  beforeAll(async () => {
    await resetMongo(store);
    await store.ensureIndexes();
  });

  afterAll(async () => {
    await store.close();
  });

  it('insertMany insère plusieurs sanctions', async () => {
    await repo.insertMany([
      makeUserActionRecord({ action: 'TIMEOUT_USER' }),
      makeUserActionRecord({ action: 'WARN_USER', userRef: 'user-8', moderationCaseId: 'case-2' }),
    ]);
    expect(await countDocuments(store, ACTIONS)).toBe(2);
  });

  it('insertMany sans enregistrement → no-op (pas d’erreur)', async () => {
    await repo.insertMany([]);
    expect(await countDocuments(store, ACTIONS)).toBe(2);
  });

  it('l’index (communityRef, userRef, createdAt) est en place', async () => {
    const db = store.dbOrThrow();
    const indexes = await db.collection(ACTIONS).listIndexes().toArray();
    const key = indexes.find((i) => i.key && i.key.communityRef === 1 && i.key.userRef === 1 && i.key.createdAt === -1);
    expect(key).toBeDefined();
  });
});