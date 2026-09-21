/**
 * Utilitaires d'accès à la base D-04 pour les tests d'intégration :
 * nettoyage et création de fixtures (Account → Community → ApiKey → Workflow → Rule).
 */

import { createHmac, randomUUID } from 'node:crypto';
import prisma, { ContentAction, Severity, UserAction, type RiskClass } from '@ai-moderator/database';

export interface SeedCommunityOptions {
  revoked?: boolean;
  rules?: Array<{ riskClass: RiskClass; severity: Severity }>;
}

export interface SeedResult {
  communityId: string;
  apiKeyRaw: string;
  apiKeyHashed: string;
}

/**
 * Vide toutes les tables de D-04 (ordre respectant les FK).
 */
export async function resetDatabase(): Promise<void> {
  await prisma.rule.deleteMany();
  await prisma.workflow.deleteMany();
  await prisma.apiKey.deleteMany();
  await prisma.community.deleteMany();
  await prisma.account.deleteMany();
}

/**
 * Crée une communauté complète avec une clé API (racine + hashée).
 * Le hash est produit localement : stocké tel quel dans `api_keys.hashedKey`.
 */
export async function seedCommunity(
  apiKeyHmacSecret: string,
  options: SeedCommunityOptions = {}
): Promise<SeedResult> {
  const apiKeyRaw = `test_${randomUUID().replace(/-/g, '')}`;
  const apiKeyHashed = hashApiKey(apiKeyRaw, apiKeyHmacSecret);

  const account = await prisma.account.create({
    data: { email: `test-${randomUUID()}@example.com` },
  });

  const community = await prisma.community.create({
    data: {
      accountId: account.id,
      name: 'Test community',
      callbackUrl: 'https://example.com/callback',
    },
  });

  await prisma.apiKey.create({
    data: {
      communityId: community.id,
      hashedKey: apiKeyHashed,
      revokedAt: options.revoked ? new Date() : null,
    },
  });

  if (options.rules && options.rules.length > 0) {
    const workflow = await prisma.workflow.create({
      data: { communityId: community.id, name: 'Default workflow' },
    });
    for (const rule of options.rules) {
      await prisma.rule.create({
        data: {
          workflowId: workflow.id,
          riskClass: rule.riskClass,
          severity: rule.severity,
          contentActions: [ContentAction.ALLOW],
          userActions: [UserAction.NONE],
        },
      });
    }
  }

  return { communityId: community.id, apiKeyRaw, apiKeyHashed };
}

/**
 * Même format de hash que `src/utils/hash.ts` (unique source de vérité).
 */
function hashApiKey(apiKey: string, secret: string): string {
  return createHmac('sha256', secret).update(apiKey).digest('hex');
}

export async function disconnectDatabase(): Promise<void> {
  await prisma.$disconnect();
}