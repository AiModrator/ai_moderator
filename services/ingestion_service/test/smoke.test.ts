/**
 * Smoke test d'infrastructure : valide la résolution du package partagé,
 * la connexion Redis et la connexion à la base D-04 depuis l'environnement
 * de test. Tagged integration.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { RiskClass } from '@ai-moderator/database';
import { RedisClient } from '../src/core/RedisClient.js';
import databaseService from '../src/core/DatabaseService.js';
import { testRedisHost, testRedisPort } from './utils/redis.js';
import { resetDatabase, disconnectDatabase } from './utils/database.js';

describe('smoke: infra shared package + deps', { tags: ['integration'] }, () => {
  let redis: RedisClient;

  beforeAll(async () => {
    redis = new RedisClient(testRedisHost(), testRedisPort());
    await redis.ping();
    await resetDatabase();
  });

  afterAll(async () => {
    await redis.disconnect();
    await disconnectDatabase();
  });

  it('RiskClass enum canonical exposes the 15 values', () => {
    expect(Object.values(RiskClass)).toHaveLength(15);
    expect(RiskClass.SPAM).toBe('SPAM');
    expect(RiskClass.OFF_TOPIC).toBe('OFF_TOPIC');
  });

  it('resolves through @ai-moderator/database and runs a real query', async () => {
    const count = await databaseService.client.account.count();
    expect(typeof count).toBe('number');
    expect(count).toBe(0);
  });

  it('redis ping returns PONG', async () => {
    await expect(redis.ping()).resolves.toBe('PONG');
  });
});