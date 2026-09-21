/**
 * Utilitaires Mongo pour les tests d'intégration D-02.
 * Réinitialise la base via dropDatabase (nettoyage complet).
 */

import { MODERATION_CASES_COLLECTION, USER_ACTIONS_COLLECTION } from '../../src/types/case.js';
import type { MongoStore } from '../../src/config/mongo.js';
import type { ModerationCase, UserActionRecord } from '../../src/types/case.js';

export async function resetMongo(store: MongoStore): Promise<void> {
  const db = await store.connect();
  await db.dropDatabase();
}

export async function countDocuments(store: MongoStore, collectionName: string): Promise<number> {
  const db = store.dbOrThrow();
  return db.collection(collectionName).countDocuments();
}

export function makeModerationCase(overrides: Partial<ModerationCase> = {}): ModerationCase {
  return {
    moderationCaseId: 'case-1',
    communityRef: 'community-1',
    accountId: 'account-1',
    contentId: 'post-42',
    contentType: 'post',
    userRef: 'user-7',
    contentTimestamp: new Date('2026-09-21T10:00:00.000Z'),
    detections: [
      { class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] },
    ],
    status: 'completed',
    decision: 'action_taken',
    contentActions: ['DELETE_POST'],
    userActions: ['TIMEOUT_USER'],
    needsReview: false,
    filtersReport: [{ filter: 'TextAIFilter', status: 'COMPLETED', attempts: 1, error: null }],
    callback: {
      url: 'https://client.example/cb',
      status: 'pending',
      attempts: 0,
      lastError: null,
      deliveredAt: null,
    },
    createdAt: new Date('2026-09-21T10:00:01.000Z'),
    updatedAt: new Date('2026-09-21T10:00:01.000Z'),
    ...overrides,
  };
}

export function makeUserActionRecord(overrides: Partial<UserActionRecord> = {}): UserActionRecord {
  return {
    communityRef: 'community-1',
    userRef: 'user-7',
    action: 'TIMEOUT_USER',
    riskClass: 'TOXICITY',
    severity: 'HIGH',
    moderationCaseId: 'case-1',
    createdAt: new Date('2026-09-21T10:00:01.000Z'),
    ...overrides,
  };
}

export { MODERATION_CASES_COLLECTION as CASES, USER_ACTIONS_COLLECTION as ACTIONS };