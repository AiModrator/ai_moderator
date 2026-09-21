/**
 * Point d'entrée de l'Action Service (bootstrap définitif — tâche 08).
 *
 * Règle : chaque service vérifie ses dépendances avant d'exécuter.
 *  1. charge la configuration ;
 *  2. vérifie D-04 (Prisma/Postgres), D-02 (Mongo) et Redis — exit 1 sinon ;
 *  3. crée les index D-02 ;
 *  4. expose `GET /health` + `GET /cases/:id` (Express) ;
 *  5. démarre le worker `decisionQueue` (BullMQ) ;
 *  6. shutdown gracieux (SIGTERM/SIGINT) : worker + HTTP + connections.
 */

import { loadSettings } from './config/settings.js';
import { Logger } from './utils/logger.js';
import { prismaClient, checkPrisma } from './config/prisma.js';
import { MongoStore } from './config/mongo.js';
import { checkRedis } from './config/redis.js';
import { CommunityRepository } from './models/communityRepository.js';
import { RuleRepository } from './models/ruleRepository.js';
import { ThresholdRepository } from './models/thresholdRepository.js';
import { ModerationCaseRepository } from './models/moderationCaseRepository.js';
import { UserActionRepository } from './models/userActionRepository.js';
import { SeverityResolver } from './service/severityResolver.js';
import { ActionResolver } from './service/actionResolver.js';
import { DecisionProcessor } from './service/decisionProcessor.js';
import { CallbackClient } from './service/callbackClient.js';
import { DecisionWorker } from './queue/decisionWorker.js';
import { HealthController } from './controllers/healthController.js';
import { CaseController } from './controllers/caseController.js';
import { createApp } from './app.js';

const settings = loadSettings();
const logger = Logger.create(settings.logLevel);

const mongo = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });

const communityRepository = new CommunityRepository(logger);
const caseRepository = new ModerationCaseRepository(mongo, logger);
const userActionRepository = new UserActionRepository(mongo, logger);

const processor = new DecisionProcessor({
  communityRepository,
  ruleRepository: new RuleRepository(logger),
  thresholdRepository: new ThresholdRepository(logger),
  severityResolver: new SeverityResolver(),
  actionResolver: new ActionResolver(),
  logger,
});

const callbackClient = new CallbackClient(
  {
    timeoutMs: settings.callbackTimeoutMs,
    maxAttempts: settings.callbackMaxAttempts,
    baseDelayMs: settings.callbackBaseDelayMs,
    maxDelayMs: settings.callbackMaxDelayMs,
  },
  logger
);

const worker = new DecisionWorker({
  settings,
  communityRepository,
  processor,
  caseRepository,
  userActionRepository,
  callbackClient,
  logger,
});

const health = new HealthController(
  {
    checkPrisma,
    checkMongo: () => mongo.ping(),
    checkRedis: () => checkRedis(settings),
  },
  logger
);

const caseApi = new CaseController(caseRepository, logger);

const app = createApp({ routers: [caseApi.router(), health.router()] });

const server = app.listen(settings.httpPort, () => {
  logger.info('action service started', { port: settings.httpPort });
});

async function shutdown(signal: string): Promise<void> {
  logger.info('action service shutting down', { signal });
  await worker.stop();
  server.close();
  await prismaClient.$disconnect().catch(() => undefined);
  await mongo.close();
  process.exit(0);
}

process.on('SIGTERM', () => void shutdown('SIGTERM'));
process.on('SIGINT', () => void shutdown('SIGINT'));

async function boot(): Promise<void> {
  try {
    await checkPrisma();
    await mongo.ping();
    await checkRedis(settings);
    await mongo.ensureIndexes();
    logger.info('dependencies ok');
  } catch (error) {
    logger.error('dependency check failed, aborting startup', { err: error });
    process.exit(1);
  }

  worker.start();
}

void boot();