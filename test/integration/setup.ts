import { PrismaClient } from '../../generated/client';
import Redis from 'ioredis';
import { MockWhopClient } from '../mocks/whopClient.mock';
import { MockAiTranslatorClient } from '../mocks/aiTranslatorClient.mock';
import { MockAiModerationClients } from '../mocks/aiModerationClients.mock';
import {prisma} from '../../src/config/prismaClient';

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
      forumLanguage: 'en',
      last_polled_at: null,
      polling_failed: false,
      last_external_post_id: null,
      last_polling_error: null,
    },
  });
}
