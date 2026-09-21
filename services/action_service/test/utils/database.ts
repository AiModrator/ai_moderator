/**
 * Utilitaires de fixtures D-04 (Postgres / Prisma) pour les tests
 * d'intégration de l'Action Service : nettoyage et création de communautés
 * complètes (Account → Community → Workflow → Rule → Threshold).
 */

import { randomUUID } from 'node:crypto';
import prisma, {
  ContentAction,
  Severity,
  UserAction,
  type RiskClass,
} from '@ai-moderator/database';

export interface RuleSeed {
  riskClass: RiskClass;
  severity: Severity;
  contentActions?: ContentAction[];
  userActions?: UserAction[];
}

export interface ThresholdSeed {
  riskClass: RiskClass;
  low?: number;
  medium?: number;
  high?: number;
  critical?: number;
}

export interface SeedCommunityOptions {
  callbackUrl?: string;
  rules?: RuleSeed[];
  thresholds?: ThresholdSeed[];
}

export interface SeedResult {
  accountId: string;
  communityId: string;
  workflowId: string | null;
}

/** Vide toutes les tables de D-04 (respect des FK). */
export async function resetDatabase(): Promise<void> {
  await prisma.rule.deleteMany();
  await prisma.threshold.deleteMany();
  await prisma.workflow.deleteMany();
  await prisma.apiKey.deleteMany();
  await prisma.community.deleteMany();
  await prisma.account.deleteMany();
}

/** Crée une communauté complète avec workflow, règles et seuils optionnels. */
export async function seedCommunity(options: SeedCommunityOptions = {}): Promise<SeedResult> {
  const account = await prisma.account.create({
    data: { email: `test-${randomUUID()}@example.com` },
  });

  const community = await prisma.community.create({
    data: {
      accountId: account.id,
      name: 'Test community',
      callbackUrl: options.callbackUrl ?? 'https://example.com/callback',
    },
  });

  let workflowId: string | null = null;
  const hasWorkflow = (options.rules && options.rules.length > 0) || options.thresholds !== undefined;

  if (hasWorkflow) {
    const workflow = await prisma.workflow.create({
      data: { communityId: community.id, name: 'Default workflow' },
    });
    workflowId = workflow.id;

    for (const rule of options.rules ?? []) {
      await prisma.rule.create({
        data: {
          workflowId: workflow.id,
          riskClass: rule.riskClass,
          severity: rule.severity,
          contentActions: rule.contentActions ?? [ContentAction.ALLOW],
          userActions: rule.userActions ?? [UserAction.NONE],
        },
      });
    }

    for (const t of options.thresholds ?? []) {
      await prisma.threshold.create({
        data: {
          workflowId: workflow.id,
          riskClass: t.riskClass,
          low: t.low ?? 0.25,
          medium: t.medium ?? 0.5,
          high: t.high ?? 0.75,
          critical: t.critical ?? 1.0,
        },
      });
    }
  }

  return { accountId: account.id, communityId: community.id, workflowId };
}

/** Seuils par défaut lorsqu'aucun `Threshold` n'existe (see main.md §3.1). */
export const DEFAULT_THRESHOLDS = {
  low: 0.25,
  medium: 0.5,
  high: 0.75,
  critical: 1.0,
} as const;

export async function disconnectDatabase(): Promise<void> {
  await prisma.$disconnect();
}