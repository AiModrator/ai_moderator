/**
 * Utilitaires Redis pour les tests d'intégration.
 * Utilise ioredis directement (pas RedisClient) pour les opérations de
 * maintenance (flush) sans passer par le code testé.
 */

import { Redis } from 'ioredis';

export function testRedisHost(): string {
  return process.env['REDIS_HOST'] ?? 'localhost';
}

export function testRedisPort(): number {
  return Number(process.env['REDIS_PORT'] ?? 6379);
}

export async function flushRedis(): Promise<void> {
  const client = new Redis({
    host: testRedisHost(),
    port: testRedisPort(),
    maxRetriesPerRequest: 3,
  });
  try {
    await client.flushdb();
  } finally {
    await client.quit();
  }
}