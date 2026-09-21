/**
 * Gestion centralisée de la configuration de l'Ingestion Service.
 * Variables lues depuis `.env.local` puis `.env`. Une configuration invalide
 * arrête le démarrage avec une erreur explicite.
 */

import dotenv from 'dotenv';

export class Settings {
  public readonly httpPort: number;

  public readonly redisHost: string;
  public readonly redisPort: number;
  public readonly redisPassword: string | undefined;

  public readonly contentQueueName: string;

  // Bucket de tokens global (throttling) — capacité, coût, refill.
  public readonly throttleCapacity: number;
  public readonly throttleCostPerToken: number;
  public readonly throttleRefillIntervalMs: number;

  // Plafond de backlog par communauté (posts en attente de traitement).
  public readonly backlogMaxPostsPerCommunity: number;

  // TTL du compteur de backlog (auto-guérison en cas de crash de process).
  public readonly backlogTtlSeconds: number;

  // TTL du cache-aside de configuration communauté (secondes).
  public readonly cacheConfigTtlSeconds: number;

  // Secret HMAC utilisé pour hasher les clés API brutes avant recherche.
  public readonly apiKeyHmacSecret: string;

  // Nombre maximal de posts par lot/payload webhook.
  public readonly maxItemsPerBatch: number;

  // Options de retry/backoff par défaut des jobs.
  public readonly queueAttempts: number;
  public readonly queueBackoffMs: number;

  constructor(env: NodeJS.ProcessEnv = process.env) {
    this.httpPort = parseIntOrThrow(env['HTTP_PORT'] ?? '3000', 'HTTP_PORT');

    this.redisHost = env['REDIS_HOST'] ?? 'localhost';
    this.redisPort = parseIntOrThrow(env['REDIS_PORT'] ?? '6379', 'REDIS_PORT');
    this.redisPassword = env['REDIS_PASSWORD'] || undefined;

    this.contentQueueName = env['CONTENT_QUEUE_NAME'] ?? 'contentQueue';

    this.throttleCapacity = parseIntOrThrow(env['THROTTLE_CAPACITY'] ?? '200', 'THROTTLE_CAPACITY');
    this.throttleCostPerToken = parseIntOrThrow(env['THROTTLE_COST_PER_TOKEN'] ?? '1', 'THROTTLE_COST_PER_TOKEN');
    this.throttleRefillIntervalMs = parseIntOrThrow(env['THROTTLE_REFILL_INTERVAL_MS'] ?? '60000', 'THROTTLE_REFILL_INTERVAL_MS');

    this.backlogMaxPostsPerCommunity = parseIntOrThrow(
      env['BACKLOG_MAX_POSTS_PER_COMMUNITY'] ?? '1000',
      'BACKLOG_MAX_POSTS_PER_COMMUNITY'
    );

    this.backlogTtlSeconds = parseIntOrThrow(env['BACKLOG_TTL_SECONDS'] ?? '3600', 'BACKLOG_TTL_SECONDS');

    this.cacheConfigTtlSeconds = parseIntOrThrow(env['CONFIG_CACHE_TTL_SECONDS'] ?? '300', 'CONFIG_CACHE_TTL_SECONDS');

    this.apiKeyHmacSecret = env['API_KEY_HMAC_SECRET'] ?? '';
    this.maxItemsPerBatch = parseIntOrThrow(env['MAX_ITEMS_PER_BATCH'] ?? '1000', 'MAX_ITEMS_PER_BATCH');

    this.queueAttempts = parseIntOrThrow(env['QUEUE_ATTEMPTS'] ?? '1', 'QUEUE_ATTEMPTS');
    this.queueBackoffMs = parseIntOrThrow(env['QUEUE_BACKOFF_MS'] ?? '1000', 'QUEUE_BACKOFF_MS');

    this.validate();
  }

  private validate(): void {
    if (this.throttleCapacity <= 0) throw new Error('THROTTLE_CAPACITY must be > 0');
    if (this.throttleCostPerToken <= 0) throw new Error('THROTTLE_COST_PER_TOKEN must be > 0');
    if (this.throttleRefillIntervalMs <= 0) throw new Error('THROTTLE_REFILL_INTERVAL_MS must be > 0');
    if (this.backlogMaxPostsPerCommunity <= 0) throw new Error('BACKLOG_MAX_POSTS_PER_COMMUNITY must be > 0');
    if (this.queueAttempts < 1) throw new Error('QUEUE_ATTEMPTS must be >= 1');
    if (this.maxItemsPerBatch < 1) throw new Error('MAX_ITEMS_PER_BATCH must be >= 1');
    if (this.apiKeyHmacSecret.length === 0) throw new Error('API_KEY_HMAC_SECRET must be set');
  }
}

export function loadSettings(): Settings {
  dotenv.config({ path: '.env.local' });
  dotenv.config();
  return new Settings(process.env);
}

function parseIntOrThrow(value: string, name: string): number {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) {
    throw new Error(`${name} must be a valid integer, got "${value}"`);
  }
  return parsed;
}