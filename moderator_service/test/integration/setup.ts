import { PrismaClient } from '../../../generated/client';
import Redis from 'ioredis';
import { MockWhopClient } from '../mocks/whopClient.mock';
import { MockAiTranslatorClient } from '../mocks/aiTranslatorClient.mock';
import { MockAiModerationClients } from '../mocks/aiModerationClients.mock';
import {prisma} from 'src/config/prismaClient';

/**
 * Configuration globale pour les tests d'intégration
 */
export interface TestConfig {
  whop: {
    postsPerCall: number;
    includeVariation: boolean;
  };
  translator: {
    minDelay: number;
    maxDelay: number;
    blockedInputs: string[];
  };
  moderation: {
    toxicityDelay: { min: number; max: number };
    sexualDelay: { min: number; max: number };
    hateDelay: { min: number; max: number };
  };
  testTimeout: number; // ms
}

/**
 * Configuration par défaut
 */
export const DEFAULT_TEST_CONFIG: TestConfig = {
  whop: {
    postsPerCall: 50,
    includeVariation: false,
  },
  translator: {
    minDelay: 50,
    maxDelay: 150,
    blockedInputs: ['BLOCKED_CONTENT', 'FORBIDDEN'],
  },
  moderation: {
    toxicityDelay: { min: 100, max: 250 },
    sexualDelay: { min: 120, max: 270 },
    hateDelay: { min: 110, max: 260 },
  },
  testTimeout: 60000, // 60 secondes
};

/**
 * Contexte des tests d'intégration
 */
export interface TestContext {
  prisma: PrismaClient;
  redis: Redis;
  whopClient: MockWhopClient;
  translatorClient: MockAiTranslatorClient;
  moderationClients: MockAiModerationClients;
  config: TestConfig;
}

/**
 * Initialiser le contexte de test
 */
export async function setupTestContext(
  config: Partial<TestConfig> = {}
): Promise<TestContext> {
  // Fusionner config
  const finalConfig: TestConfig = {
    ...DEFAULT_TEST_CONFIG,
    ...config,
  };

  // Initialiser Prisma
;

  // Initialiser Redis
  const redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    db: parseInt(process.env.REDIS_DB || '0'),
    retryStrategy: (times) => Math.min(times * 50, 2000),
  });

  // Initialiser les mocks
  const whopClient = new MockWhopClient({
    postsPerCall: finalConfig.whop.postsPerCall,
    includeVariation: finalConfig.whop.includeVariation,
  });

  const translatorClient = new MockAiTranslatorClient({
    minDelay: finalConfig.translator.minDelay,
    maxDelay: finalConfig.translator.maxDelay,
    blockedInputs: finalConfig.translator.blockedInputs,
  });

  const moderationClients = new MockAiModerationClients({
    toxicityDelay: finalConfig.moderation.toxicityDelay,
    sexualDelay: finalConfig.moderation.sexualDelay,
    hateDelay: finalConfig.moderation.hateDelay,
  });

  return {
    prisma,
    redis,
    whopClient,
    translatorClient,
    moderationClients,
    config: finalConfig,
  };
}

/**
 * Nettoyer le contexte de test (sans supprimer les données BD)
 */
export async function teardownTestContext(context: TestContext): Promise<void> {
  // Arrêter les workers (à implémenter selon votre structure)
  // await stopAllWorkers();

  // Vider les queues Redis
  try {
    const keys = await context.redis.keys('bull:*');
    if (keys.length > 0) {
      await context.redis.del(...keys);
    }
  } catch (error) {
    console.warn('Error clearing Redis queues:', error);
  }

  // Fermer les connexions
  await context.prisma.$disconnect();
  await context.redis.quit();

  console.log('Test context torn down (BD data preserved)');
}

/**
 * Créer un forum de test dans la BD
 */
export async function createTestForum(
  prisma: PrismaClient,
  companyId: string = 'test_company_1'
) {
  return await prisma.forum.create({
    data: {
      id: `test_forum_${Date.now()}`,
      experience_id: `exp_${Date.now()}`,
      experience_name: 'Integration Test Forum',
      company_id: companyId,
      is_moderated: true,
      ban_media: false,
      who_can_post: 'members',
      who_can_comment: 'members',
      email_notification_preference: 'weekly',
      forumDescription: 'Test forum for integration tests',
      forumLanguage: 'fr',
      last_polled_at: null,
      polling_failed: false,
      last_external_post_id: null,
      last_polling_error: null,
    },
  });
}


export async function createTestUser(
  prisma: PrismaClient,
  overrides: any = {}
) {
  const timestamp = Date.now();
  const id = overrides.id || 'test_user_1'; // On définit l'ID d'abord

  const userData = {
    id,
    username: overrides.username || `user_${timestamp}`,
    name: overrides.name || "Jean Testeur",
    bio: overrides.bio || "Ceci est une bio de test pour l'IA.",
    profile_picture_url: overrides.profile_picture_url || "https://avatar.iran.liara.run/public",
    created_at: overrides.created_at || new Date(),
    ...overrides
  };

  return await prisma.user.upsert({
    where: { id: id }, // Cherche par ID
    update: userData,  // Si trouvé, met à jour avec les nouvelles valeurs
    create: userData,  // Si non trouvé, crée l'entrée
  });
}


export async function createTestCompany(
  prisma: PrismaClient,
  userId: string = 'test_user_1',
  overrides: any = {}
) {
  const id = overrides.id || "test_company_1";

  const companyData = {
    id: id,
    title: overrides.title || "Ma Super Entreprise de Test",
    description: overrides.description || "Une description mockée pour les tests",
    verified: overrides.verified ?? true,
    business_type: overrides.business_type || "SaaS",
    industry_type: overrides.industry_type || "Technology",
    send_customer_emails: overrides.send_customer_emails ?? false,
    created_at: overrides.created_at || new Date(),
    updated_at: overrides.updated_at || new Date(),
    member_count: overrides.member_count || 10,
    route: overrides.route || "/test-company-route",
    logo_url: overrides.logo_url || "https://picsum.photos/200",
    user_id: userId,
    ...overrides
  };

  return await prisma.company.upsert({
    where: { id: id },
    update: companyData,
    create: companyData,
  });
}



export async function clearDatabase() {
  try {
    // 1. On récupère tous les noms de tables du schéma public (PostgreSQL)
    // On exclut la table des migrations de Prisma
    const tablenames = await prisma.$queryRaw<Array<{ tablename: string }>>`
      SELECT tablename FROM pg_tables 
      WHERE schemaname = 'public' 
      AND tablename NOT IN ('_prisma_migrations')
    `;

    // 2. On formate les noms pour la requête SQL
    const tables = tablenames
      .map(({ tablename }) => `"${tablename}"`)
      .join(', ');

    if (tables.length > 0) {
      // 3. TRUNCATE est beaucoup plus rapide que DELETE
      // CASCADE permet de supprimer les données même avec des clés étrangères
      // RESTART IDENTITY réinitialise les compteurs d'Auto-increment (id: 1, 2, 3...)
      await prisma.$executeRawUnsafe(`TRUNCATE TABLE ${tables} RESTART IDENTITY CASCADE;`);
      console.log('✅ Base de données vidée avec succès.');
    }
  } catch (error) {
    console.error('❌ Erreur lors du vidage de la base de données:', error);
    throw error;
  }
}


export async function clearRedis() {
  // Avec ioredis
  const redis = new Redis();
  await redis.flushdb();
  console.log("✅ Redis vidé");
}



// Fonction pour attendre qu'une queue spécifique soit vide et inactive
// Dans test/integration/setup.ts
export const waitForQueue = async (queue: any) => {
    // 1. Attendre un court instant que le job soit au moins enregistré dans Redis
    await new Promise(res => setTimeout(res, 500)); 

    let isWorking = true;
    while (isWorking) {
        const counts = await queue.getJobCounts();
        // On considère que c'est fini seulement s'il n'y a plus rien en attente, 
        // plus rien en cours (active) et plus rien en délai (backoff)
        const totalPending = counts.waiting + counts.active + counts.delayed;
        
        if (totalPending === 0) {
            isWorking = false;
        } else {
            await new Promise(res => setTimeout(res, 1000));
        }
    }
    // 2. Petit délai de sécurité pour laisser les scripts Lua de BullMQ finir
    await new Promise(res => setTimeout(res, 200)); 
};