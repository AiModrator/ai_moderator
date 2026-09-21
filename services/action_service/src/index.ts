/**
 * Point d'entrée de l'Action Service (bootstrap minimal — tâche 01).
 *
 * Règle : chaque service vérifie ses dépendances avant d'exécuter.
 *  1. charge la configuration ;
 *  2. vérifie D-04 (Prisma/Postgres), D-02 (Mongo) et Redis ;
 *  3. expose `GET /health` ;
 *  4. shutdown gracieux (SIGTERM/SIGINT).
 *
 * Le worker `decisionQueue` est branché dans la tâche 07 et le bootstrap
 * définitif dans la tâche 08.
 */

import { loadSettings } from './config/settings.js';
import { Logger } from './utils/logger.js';
import { prismaClient, checkPrisma } from './config/prisma.js';
import { MongoStore } from './config/mongo.js';
import { checkRedis } from './config/redis.js';
import { HealthController } from './controllers/healthController.js';
import { createApp } from './app.js';

const settings = loadSettings();
const logger = Logger.create(settings.logLevel);

const mongo = new MongoStore({ mongodbUri: settings.mongodbUri, mongodbDb: settings.mongodbDb });

const health = new HealthController(
  {
    checkPrisma,
    checkMongo: () => mongo.ping(),
    checkRedis: () => checkRedis(settings),
  },
  logger
);

const app = createApp({ routers: [health.router()] });

const server = app.listen(settings.httpPort, () => {
  logger.info('action service started', { port: settings.httpPort });
});

async function shutdown(): Promise<void> {
  logger.info('action service shutting down');
  server.close();
  await prismaClient.$disconnect().catch(() => undefined);
  await mongo.close();
  process.exit(0);
}

process.on('SIGTERM', () => void shutdown());
process.on('SIGINT', () => void shutdown());

async function boot(): Promise<void> {
  try {
    await checkPrisma();
    await mongo.ping();
    await checkRedis(settings);
    logger.info('dependencies ok');
  } catch (error) {
    logger.error('dependency check failed, aborting startup', { err: error });
    process.exit(1);
  }
}

void boot();