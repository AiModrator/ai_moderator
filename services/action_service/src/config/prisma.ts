/**
 * Client D-04 (Postgres / Prisma) — client partagé `@ai-moderator/database`.
 * Une seule instance réutilisée par tout le service (pas d'épuisement de pool).
 */

import prisma, { checkDbConnection } from '@ai-moderator/database';

declare global {
  // eslint-disable-next-line no-var
  var __actionPrisma: typeof prisma | undefined;
}

const client: typeof prisma = globalThis.__actionPrisma ?? prisma;
globalThis.__actionPrisma = client;

export const prismaClient: typeof prisma = client;

/** Vérification de disponibilité de D-04 au démarrage (et /health). */
export async function checkPrisma(): Promise<void> {
  await checkDbConnection();
}