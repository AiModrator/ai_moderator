/**
 * Point d'entrée de l'Ingestion Service.
 *
 * Séquence de démarrage (règle : vérifier les dépendances avant d'exécuter) :
 *   1. charge la configuration ;
 *   2. vérifie la disponibilité de Redis et de la base D-04 ;
 *   3. assemble les dépendances (repositories, cache, throttling, dispatch) ;
 *   4. démarre le serveur HTTP.
 */

import { loadSettings } from './config/settings.js';
import { Logger } from './config/logger.js';
import { RedisClient } from './core/RedisClient.js';
import { RedisService } from './core/RedisService.js';
import databaseService from './core/DatabaseService.js';
import { BullMQClient } from './core/BullMQClient.js';
import { StdoutMetricsProvider } from './core/metrics/StdoutMetricsProvider.js';
import { ApiKeyRepository } from './repositories/ApiKeyRepository.js';
import { WorkflowRepository } from './repositories/WorkflowRepository.js';
import { AuthManager } from './core/AuthManager.js';
import { ThrottlingService } from './core/ThrottlingService.js';
import { DataDispatcher } from './core/DataDispatcher.js';
import { Validator } from './core/Validator.js';
import { IngestionController } from './controllers/IngestionController.js';
import { createApp } from './config/express.js';

const settings = loadSettings();
const logger = new Logger();

const redisClient = new RedisClient(settings.redisHost, settings.redisPort, settings.redisPassword);
const redisService = new RedisService(redisClient);

const metrics = new StdoutMetricsProvider();

const apiKeyRepository = new ApiKeyRepository();
const workflowRepository = new WorkflowRepository();

const authManager = new AuthManager(
  apiKeyRepository,
  redisService,
  settings.apiKeyHmacSecret,
  settings.cacheConfigTtlSeconds,
  logger
);

const throttlingService = new ThrottlingService(
  redisService,
  metrics,
  {
    capacity: settings.throttleCapacity,
    costPerToken: settings.throttleCostPerToken,
    refillIntervalMs: settings.throttleRefillIntervalMs,
  },
  logger
);

const bullMQClient = new BullMQClient(
  {
    host: settings.redisHost,
    port: settings.redisPort,
    ...(settings.redisPassword ? { password: settings.redisPassword } : {}),
  },
  { defaultAttempts: settings.queueAttempts, defaultBackoffMs: settings.queueBackoffMs }
);

const dataDispatcher = new DataDispatcher(bullMQClient, settings.contentQueueName, logger);

const validator = new Validator({ maxItemsPerBatch: settings.maxItemsPerBatch });

const controller = new IngestionController({
  validator,
  authManager,
  workflowRepository,
  throttlingService,
  dataDispatcher,
  redisService,
  logger,
  cacheConfigTtlSeconds: settings.cacheConfigTtlSeconds,
  backlogMaxPostsPerCommunity: settings.backlogMaxPostsPerCommunity,
  backlogTtlSeconds: settings.backlogTtlSeconds,
});

const app = createApp({ controller, logger });

const server = app.listen(settings.httpPort, () => {
  logger.info('ingestion service started', { port: settings.httpPort });
});

async function shutdown(): Promise<void> {
  logger.info('ingestion service shutting down');
  server.close();
  await redisClient.disconnect().catch(() => undefined);
  await databaseService.client.$disconnect().catch(() => undefined);
  process.exit(0);
}

process.on('SIGTERM', () => void shutdown());
process.on('SIGINT', () => void shutdown());

async function boot(): Promise<void> {
  try {
    await redisClient.ping();
    await databaseService.checkConnection();
  } catch (error) {
    logger.error('dependency check failed, aborting startup', { err: error });
    process.exit(1);
  }
}

void boot();