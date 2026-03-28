import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';

import { PrismaClient } from './generated/client.js';
const connectionString = `${process.env.DATABASE_URL}`;


// database/prismaClient.ts




const pool = new pg.Pool({ connectionString });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

export async function checkDbConnection() {
  try {
    await prisma.$connect();
    console.log('✅ Connexion à la base de données réussie via Prisma !');
  } catch (error) {
    console.error('❌ Impossible de se connecter à la base de données :', error);
    throw error;
  }
}

export { prisma };