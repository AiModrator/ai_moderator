/**
 * Tâche 01 — `GET /health` (disponibilité réelle des dépendances).
 * Tests d'intégration : Postgres, Redis et Mongo réels (docker).
 */

import { describe, it, expect, afterAll } from 'vitest';
import request from 'supertest';
import { Settings } from '../../src/config/settings.js';
import { Logger } from '../../src/utils/logger.js';
import { checkPrisma } from '../../src/config/prisma.js';
import { MongoStore } from '../../src/config/mongo.js';
import { checkRedis } from '../../src/config/redis.js';
import { HealthController } from '../../src/controllers/healthController.js';
import { createApp } from '../../src/app.js';
import { disconnectDatabase } from '../utils/database.js';

const settings = new Settings(process.env as NodeJS.ProcessEnv);

function buildApp(redisCheck: () => Promise<void>) {
  const logger = Logger.create('silent');
  const mongo = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });
  const health = new HealthController(
    {
      checkPrisma,
      checkMongo: () => mongo.ping(),
      checkRedis: redisCheck,
    },
    logger
  );
  return createApp({ routers: [health.router()] });
}

describe('GET /health', { tags: ['integration'] }, () => {
  afterAll(async () => {
    await disconnectDatabase();
  });

  it('200 quand Postgres, Mongo et Redis sont joignables', async () => {
    const res = await request(buildApp(() => checkRedis(settings))).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.dependencies).toEqual({ postgres: true, mongo: true, redis: true });
  });

  it('503 quand Redis est injoignable (dégradation partielle)', async () => {
    const badSettings = new Settings({
      ...(process.env as NodeJS.ProcessEnv),
      REDIS_PORT: '6399', // aucun redis sur ce port
    } as NodeJS.ProcessEnv);

    const res = await request(buildApp(() => checkRedis(badSettings))).get('/health');
    expect(res.status).toBe(503);
    expect(res.body.status).toBe('degraded');
    expect(res.body.dependencies).toMatchObject({ postgres: true, mongo: true, redis: false });
  });
});