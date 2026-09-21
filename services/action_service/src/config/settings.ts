/**
 * Gestion centralisée de la configuration de l'Action Service.
 * Variables lues depuis `.env.local` puis `.env`. Une config invalide
 * arrête le démarrage avec une erreur explicite.
 */

import dotenv from 'dotenv';

export interface ThresholdDefaults {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export class Settings {
  public readonly httpPort: number;

  public readonly databaseUrl: string;

  public readonly redisHost: string;
  public readonly redisPort: number;
  public readonly redisPassword: string | undefined;

  public readonly decisionQueueName: string;
  public readonly decisionWorkerConcurrency: number;

  public readonly mongodbUri: string;
  public readonly mongodbDb: string;

  public readonly thresholdDefaults: ThresholdDefaults;

  public readonly callbackTimeoutMs: number;
  public readonly callbackMaxAttempts: number;
  public readonly callbackBaseDelayMs: number;
  public readonly callbackMaxDelayMs: number;

  public readonly logLevel: string;

  constructor(env: NodeJS.ProcessEnv = process.env) {
    this.httpPort = parseIntOrThrow(env['HTTP_PORT'] ?? '3001', 'HTTP_PORT');

    this.databaseUrl = env['DATABASE_URL'] ?? '';

    this.redisHost = env['REDIS_HOST'] ?? 'localhost';
    this.redisPort = parseIntOrThrow(env['REDIS_PORT'] ?? '6379', 'REDIS_PORT');
    this.redisPassword = env['REDIS_PASSWORD'] || undefined;

    this.decisionQueueName = env['DECISION_QUEUE_NAME'] ?? 'decisionQueue';
    this.decisionWorkerConcurrency = parseIntOrThrow(
      env['DECISION_WORKER_CONCURRENCY'] ?? '5',
      'DECISION_WORKER_CONCURRENCY'
    );

    this.mongodbUri = env['MONGODB_URI'] ?? 'mongodb://localhost:27017';
    this.mongodbDb = env['MONGODB_DB'] ?? 'ai_moderator_history';

    this.thresholdDefaults = {
      low: parseFloatOrThrow(env['DEFAULT_LOW'] ?? '0.25', 'DEFAULT_LOW'),
      medium: parseFloatOrThrow(env['DEFAULT_MEDIUM'] ?? '0.50', 'DEFAULT_MEDIUM'),
      high: parseFloatOrThrow(env['DEFAULT_HIGH'] ?? '0.75', 'DEFAULT_HIGH'),
      critical: parseFloatOrThrow(env['DEFAULT_CRITICAL'] ?? '1.00', 'DEFAULT_CRITICAL'),
    };

    this.callbackTimeoutMs = parseIntOrThrow(env['CALLBACK_TIMEOUT_MS'] ?? '5000', 'CALLBACK_TIMEOUT_MS');
    this.callbackMaxAttempts = parseIntOrThrow(env['CALLBACK_MAX_ATTEMPTS'] ?? '5', 'CALLBACK_MAX_ATTEMPTS');
    this.callbackBaseDelayMs = parseIntOrThrow(env['CALLBACK_BASE_DELAY_MS'] ?? '1000', 'CALLBACK_BASE_DELAY_MS');
    this.callbackMaxDelayMs = parseIntOrThrow(env['CALLBACK_MAX_DELAY_MS'] ?? '30000', 'CALLBACK_MAX_DELAY_MS');

    this.logLevel = env['LOG_LEVEL'] ?? 'info';

    this.validate();
  }

  private validate(): void {
    if (!this.databaseUrl) throw new Error('DATABASE_URL is required');
    if (this.httpPort <= 0) throw new Error('HTTP_PORT must be > 0');
    if (this.redisPort <= 0) throw new Error('REDIS_PORT must be > 0');
    if (this.decisionWorkerConcurrency < 1) throw new Error('DECISION_WORKER_CONCURRENCY must be >= 1');
    if (this.callbackMaxAttempts < 1) throw new Error('CALLBACK_MAX_ATTEMPTS must be >= 1');
    if (this.callbackBaseDelayMs < 0 || this.callbackMaxDelayMs < this.callbackBaseDelayMs) {
      throw new Error('CALLBACK_BASE_DELAY_MS must be >= 0 and CALLBACK_MAX_DELAY_MS >= CALLBACK_BASE_DELAY_MS');
    }
    if (this.callbackTimeoutMs <= 0) throw new Error('CALLBACK_TIMEOUT_MS must be > 0');

    const { low, medium, high, critical } = this.thresholdDefaults;
    if (!(0 <= low && low <= medium && medium <= high && high <= critical && critical <= 1)) {
      throw new Error('DEFAULT thresholds must respect 0 <= low <= medium <= high <= critical <= 1');
    }
  }
}

export function loadSettings(): Settings {
  dotenv.config({ path: '.env.local' });
  dotenv.config();
  return new Settings(process.env);
}

function parseIntOrThrow(value: string, name: string): number {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) throw new Error(`${name} must be a valid integer, got "${value}"`);
  return parsed;
}

function parseFloatOrThrow(value: string, name: string): number {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) throw new Error(`${name} must be a valid number, got "${value}"`);
  return parsed;
}