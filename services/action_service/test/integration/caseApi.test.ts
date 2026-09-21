/**
 * Tâche 08 — API de lecture : `GET /cases/:id` (200/404) + `/health`.
 * Tests d'intégration (Mongo réel pour le cas, deps réelles pour /health).
 */

import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Settings } from '../../src/config/settings.js';
import { MongoStore } from '../../src/config/mongo.js';
import { checkPrisma } from '../../src/config/prisma.js';
import { checkRedis } from '../../src/config/redis.js';
import { ModerationCaseRepository } from '../../src/models/moderationCaseRepository.js';
import { CaseController } from '../../src/controllers/caseController.js';
import { HealthController } from '../../src/controllers/healthController.js';
import { createApp } from '../../src/app.js';
import { Logger } from '../../src/utils/logger.js';
import { resetMongo, makeModerationCase } from '../utils/mongo.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);
const store = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
const logger = Logger.create('silent');
const repo = new ModerationCaseRepository(store, logger);

describe('CaseApi', { tags: ['integration'] }, () => {
  beforeAll(async () => {
    await resetMongo(store);
    await store.ensureIndexes();
  });

  afterAll(async () => {
    await store.close();
  });

  it('GET /cases/:id → 200, cas complet, dates ISO, sans _id', async () => {
    const cse = makeModerationCase({
      moderationCaseId: 'case-api-1',
      decision: 'action_taken',
      status: 'pending_review',
      needsReview: true,
      contentActions: ['DELETE_POST', 'FLAG_FOR_REVIEW'],
      userActions: ['BAN_USER'],
      callback: {
        url: 'https://client.example/cb',
        status: 'failed',
        attempts: 3,
        lastError: 'HTTP 503',
        deliveredAt: null,
      },
      createdAt: new Date('2026-09-21T10:00:00.000Z'),
    });
    await repo.upsert(cse);

    const app = createApp({ routers: [new CaseController(repo, logger).router()] });
    const res = await request(app).get('/cases/case-api-1').expect(200);

    const body = res.body as Record<string, unknown>;
    expect(body).toMatchObject({
      moderationCaseId: 'case-api-1',
      communityRef: 'community-1',
      decision: 'action_taken',
      status: 'pending_review',
      needsReview: true,
      contentActions: ['DELETE_POST', 'FLAG_FOR_REVIEW'],
    });
    expect(body['_id']).toBeUndefined();
    expect(body['createdAt']).toBe('2026-09-21T10:00:00.000Z');
    expect(body['contentTimestamp']).toBe('2026-09-21T10:00:00.000Z');
    expect(body['updatedAt']).toBeTypeOf('string');
    expect((body['callback'] as { deliveredAt: unknown }).deliveredAt).toBeNull();
  });

  it('GET /cases/inconnu → 404 case_not_found', async () => {
    const app = createApp({ routers: [new CaseController(repo, logger).router()] });
    const res = await request(app).get('/cases/absent').expect(404);
    expect(res.body).toEqual({ error: 'case_not_found', moderationCaseId: 'absent' });
  });

  it('GET /cases/:id → 500 si D-02 injoignable', async () => {
    const failingStore = new MongoStore({ mongodbUri: 'mongodb://127.0.0.1:27018', mongodbDb: 'x' });
    const failingRepo = new ModerationCaseRepository(failingStore, logger);
    const app = createApp({ routers: [new CaseController(failingRepo, logger).router()] });
    await request(app).get('/cases/any').expect(500);
  });

  it('GET /health → 200 ok quand toutes les deps répondent', async () => {
    const health = new HealthController(
      { checkPrisma, checkMongo: () => store.ping(), checkRedis: () => checkRedis(settings) },
      logger
    );
    const app = createApp({ routers: [health.router()] });
    const res = await request(app).get('/health').expect(200);
    expect(res.body).toMatchObject({ status: 'ok', dependencies: { postgres: true, mongo: true, redis: true } });
  });

  it('GET /health → 503 degraded dès qu’une dep échoue', async () => {
    const failing = new HealthController(
      {
        checkPrisma: async () => undefined,
        checkMongo: async () => {
          throw new Error('mongo down');
        },
        checkRedis: async () => undefined,
      },
      logger
    );
    const app = createApp({ routers: [failing.router()] });
    const res = await request(app).get('/health').expect(503);
    expect(res.body).toMatchObject({ status: 'degraded', dependencies: { postgres: true, mongo: false, redis: true } });
  });
});