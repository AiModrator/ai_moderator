/**
 * Configuration Redis — uniquement pour BullMQ (pas de cache applicatif).
 */

import { Redis } from 'ioredis';
import type { RedisOptions } from 'bullmq';
import type { Settings } from './settings.js';

/**
 * Connexion partagée BullMQ. `maxRetriesPerRequest: null` est imposé par
 * BullMQ (file d'attente bloquante bloquant).
 */
export function bullmqConnection(settings: Settings): RedisOptions {
  return {
    host: settings.redisHost,
    port: settings.redisPort,
    ...(settings.redisPassword ? { password: settings.redisPassword } : {}),
    maxRetriesPerRequest: null,
  };
}

/** Ping Redis (health-check de démarrage / `/health`). */
export async function checkRedis(settings: Settings): Promise<void> {
  const client = new Redis({
    host: settings.redisHost,
    port: settings.redisPort,
    ...(settings.redisPassword ? { password: settings.redisPassword } : {}),
    maxRetriesPerRequest: 2,
  });
  try {
    await client.ping();
  } finally {
    await client.quit();
  }
}