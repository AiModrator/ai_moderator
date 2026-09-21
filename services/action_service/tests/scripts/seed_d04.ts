/**
 * Seed D-04 (Postgres / Prisma) — communauté + workflow + règles + seuils.
 *
 * Usage : `npx tsx tests/scripts/seed_d04.ts [name]`
 * Sortie : l'identifiant de la communauté créée (ligo pour publishDecision
 * ou un e2e manuel). Inclut une calibration personnalisée par défaut sur
 * TOXICITY (critical abaissé à 0.90) pour valider le moteur de décision.
 */

import { randomUUID } from 'node:crypto';
import { ContentAction, Severity, UserAction } from '@ai-moderator/database';
import prisma from '@ai-moderator/database';

const name = process.argv[2] ?? 'seed-community';

async function main(): Promise<void> {
  const communityName = `${name}-${randomUUID().slice(0, 8)}`;

  const account = await prisma.account.create({
    data: { email: `${communityName}@example.com` },
  });

  const community = await prisma.community.create({
    data: {
      accountId: account.id,
      name: communityName,
      callbackUrl: process.env.CALLBACK_URL ?? 'https://example.com/callback',
    },
  });

  const workflow = await prisma.workflow.create({
    data: { communityId: community.id, name: 'Seed workflow' },
  });

  await prisma.threshold.create({
    data: {
      workflowId: workflow.id,
      riskClass: 'TOXICITY',
      low: 0.25,
      medium: 0.5,
      high: 0.75,
      critical: 0.9,
    },
  });

  await prisma.rule.create({
    data: {
      workflowId: workflow.id,
      riskClass: 'TOXICITY',
      severity: Severity.CRITICAL,
      contentActions: [ContentAction.DELETE_POST],
      userActions: [UserAction.BAN_USER],
    },
  });

  await prisma.rule.create({
    data: {
      workflowId: workflow.id,
      riskClass: 'TOXICITY',
      severity: Severity.MEDIUM,
      contentActions: [ContentAction.HIDE_POST],
      userActions: [UserAction.WARN_USER],
    },
  });

  console.log(JSON.stringify({ communityId: community.id, workflowId: workflow.id }, null, 2));
  await prisma.$disconnect();
}

main().catch((error) => {
  console.error('seed failed', error);
  process.exit(1);
});