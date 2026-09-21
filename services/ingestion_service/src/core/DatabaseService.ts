/**
 * DatabaseService — wrapper exposant le client Prisma partagé
 * (`@ai-moderator/database`, base D-04) aux repositories du service.
 *
 * Une seule instance de `PrismaClient` est réutilisée par tout le service
 * (évite l'épuisement du pool de connexions).
 */

import prisma, { checkDbConnection } from '@ai-moderator/database';

declare global {
  // eslint-disable-next-line no-var
  var __ingestionPrisma: typeof prisma | undefined;
}

// Reuse a single PrismaClient instance across hot-reloads (esbuild/tsx).
const client: typeof prisma = globalThis.__ingestionPrisma ?? prisma;
globalThis.__ingestionPrisma = client;

export class DatabaseService {
  readonly client: typeof prisma = client;

  /**
   * Vérifie au démarrage que la base D-04 est joignable (règle : chaque
   * service vérifie ses dépendances avant d'exécuter).
   */
  async checkConnection(): Promise<void> {
    await checkDbConnection();
  }
}

const databaseService = new DatabaseService();
export default databaseService;