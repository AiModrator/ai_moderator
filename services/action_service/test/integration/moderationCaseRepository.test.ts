/**
 * Tâche 04 — ModerationCaseRepository (D-02, Mongo réel).
 * Tests d'intégration : upsert idempotent, findById, updateCallback.
 */

import { beforeAll, afterAll, describe, it, expect } from 'vitest';
import { Settings } from '../../src/config/settings.js';
import { MongoStore } from '../../src/config/mongo.js';
import { ModerationCaseRepository } from '../../src/models/moderationCaseRepository.js';
import { Logger } from '../../src/utils/logger.js';
import { resetMongo, makeModerationCase, CASES, countDocuments } from '../utils/mongo.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);
const store = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
const logger = Logger.create('silent');
const repo = new ModerationCaseRepository(store, logger);

describe('ModerationCaseRepository', { tags: ['integration'] }, () => {
  beforeAll(async () => {
    await resetMongo(store);
    await store.ensureIndexes();
  });

  afterAll(async () => {
    await store.close();
  });

  it('upsert insère puis remplace sans doublon (idempotence)', async () => {
    const cse = makeModerationCase({});

    await repo.upsert({ ...cse, decision: 'action_taken', contentActions: ['DELETE_POST'] });
    await repo.upsert({ ...cse, updatedAt: new Date(), contentActions: ['DELETE_POST', 'HIDE_POST'] });

    expect(await countDocuments(store, CASES)).toBe(1);
    const reloaded = await repo.findById(cse.moderationCaseId);
    expect(reloaded).not.toBeNull();
    expect(reloaded!.contentActions).toEqual(['DELETE_POST', 'HIDE_POST']);
  });

  it('findById retourne le cas complet (détections + callback + needsReview)', async () => {
    const cse = makeModerationCase({
      moderationCaseId: 'case-complete',
      status: 'pending_review',
      needsReview: true,
      callback: { url: 'https://x.example', status: 'pending', attempts: 1, lastError: null, deliveredAt: null },
    });
    await repo.upsert(cse);

    const found = await repo.findById('case-complete');
    expect(found).toMatchObject({
      moderationCaseId: 'case-complete',
      status: 'pending_review',
      needsReview: true,
      detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH' }],
    });
    expect(found?.contentTimestamp).toBeInstanceOf(Date);
  });

  it('findById retourne null si absent', async () => {
    expect(await repo.findById('absent')).toBeNull();
  });

  it('updateCallback modifie uniquement le champ callback', async () => {
    const cse = makeModerationCase({ moderationCaseId: 'case-callback' });
    await repo.upsert(cse);

    await repo.updateCallback('case-callback', {
      url: 'https://client.example/cb',
      status: 'delivered',
      attempts: 2,
      lastError: null,
      deliveredAt: new Date('2026-09-21T10:00:05.000Z'),
    });

    const found = await repo.findById('case-callback');
    expect(found?.callback).toMatchObject({ status: 'delivered', attempts: 2 });
    expect(found?.callback.deliveredAt).toBeInstanceOf(Date);
    // Le reste du document n'est pas écrasé
    expect(found?.decision).toBe('action_taken');
    expect(found?.contentActions).toEqual(['DELETE_POST']);
  });
});