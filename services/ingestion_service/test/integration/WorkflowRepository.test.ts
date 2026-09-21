/**
 * Tâche 07 — WorkflowRepository (classes de risque actives, dédupliquées).
 * Tests d'intégration : base Postgres D-04 réelle.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import prisma, { RiskClass, Severity } from '@ai-moderator/database';
import { WorkflowRepository } from '../../src/repositories/WorkflowRepository.js';
import { resetDatabase, disconnectDatabase, seedCommunity } from '../utils/database.js';

const SECRET = 'test-hmac-secret';

describe('WorkflowRepository', { tags: ['integration'] }, () => {
  const repository = new WorkflowRepository();

  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('3 classes distinctes → retourne exactement 3 classes', async () => {
    const seed = await seedCommunity(SECRET, {
      rules: [
        { riskClass: RiskClass.SPAM, severity: Severity.LOW },
        { riskClass: RiskClass.TOXICITY, severity: Severity.HIGH },
        { riskClass: RiskClass.OFF_TOPIC, severity: Severity.MEDIUM },
      ],
    });

    const classes = await repository.getActiveRiskClasses(seed.communityId);

    expect(classes).toHaveLength(3);
    expect(new Set(classes)).toEqual(
      new Set([RiskClass.SPAM, RiskClass.TOXICITY, RiskClass.OFF_TOPIC])
    );
  });

  it('classes dupliquées entre règles → dédupliquées', async () => {
    const seed = await seedCommunity(SECRET, {
      rules: [
        { riskClass: RiskClass.SPAM, severity: Severity.LOW },
        { riskClass: RiskClass.SPAM, severity: Severity.HIGH },
        { riskClass: RiskClass.TOXICITY, severity: Severity.MEDIUM },
      ],
    });

    const classes = await repository.getActiveRiskClasses(seed.communityId);

    expect(classes).toHaveLength(2);
    expect(new Set(classes)).toEqual(new Set([RiskClass.SPAM, RiskClass.TOXICITY]));
  });

  it('communauté sans workflow → tableau vide', async () => {
    const seed = await seedCommunity(SECRET);
    await expect(repository.getActiveRiskClasses(seed.communityId)).resolves.toEqual([]);
  });

  it('workflow sans règle → tableau vide', async () => {
    const seed = await seedCommunity(SECRET);
    await prisma.workflow.create({
      data: { communityId: seed.communityId, name: 'Empty workflow' },
    });

    await expect(repository.getActiveRiskClasses(seed.communityId)).resolves.toEqual([]);
  });
});