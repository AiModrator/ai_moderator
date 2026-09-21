/**
 * Tâche 02 — Repositories D-04 (Community / Rule / Threshold).
 * Tests d'intégration : base Postgres réelle (docker), seed D-04.
 */

import { beforeAll, afterAll, describe, it, expect } from 'vitest';
import { ContentAction, Severity, UserAction } from '@ai-moderator/database';
import { CommunityRepository } from '../../src/models/communityRepository.js';
import { RuleRepository } from '../../src/models/ruleRepository.js';
import { ThresholdRepository } from '../../src/models/thresholdRepository.js';
import { CommunityNotFoundError } from '../../src/exceptions/index.js';
import { Logger } from '../../src/utils/logger.js';
import { resetDatabase, seedCommunity, disconnectDatabase } from '../utils/database.js';

const logger = Logger.create('silent');

describe('CommunityRepository.findByRef', { tags: ['integration'] }, () => {
  const repo = new CommunityRepository(logger);

  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('retourne context complet pour une communauté avec workflow', async () => {
    const seed = await seedCommunity({
      callbackUrl: 'https://client.example/cb',
      rules: [{ riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] }],
    });

    const ctx = await repo.findByRef(seed.communityId);
    expect(ctx.communityId).toBe(seed.communityId);
    expect(ctx.accountId).toBe(seed.accountId);
    expect(ctx.callbackUrl).toBe('https://client.example/cb');
    expect(ctx.workflowId).toBe(seed.workflowId);
  });

  it('retourne workflowId=null pour une communauté sans workflow', async () => {
    const seed = await seedCommunity();
    const ctx = await repo.findByRef(seed.communityId);
    expect(ctx.workflowId).toBeNull();
    expect(ctx.callbackUrl).toBe('https://example.com/callback');
  });

  it('communityRef inconnu → CommunityNotFoundError (sans retry)', async () => {
    await expect(repo.findByRef('does-not-exist')).rejects.toBeInstanceOf(CommunityNotFoundError);
  });
});

describe('RuleRepository.findByWorkflow', { tags: ['integration'] }, () => {
  const repo = new RuleRepository(logger);

  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('retourne les règles d’un workflow', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
        { riskClass: 'SEXUAL', severity: Severity.CRITICAL, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.BAN_USER] },
      ],
    });

    const rules = await repo.findByWorkflow(seed.workflowId!);
    expect(rules).toHaveLength(2);
    expect(rules.map((r) => r.riskClass).sort()).toEqual(['SEXUAL', 'TOXICITY']);
    expect(rules.find((r) => r.riskClass === 'TOXICITY')?.contentActions).toContain(ContentAction.DELETE_POST);
  });

  it('retourne une liste vide pour un workflow sans règle', async () => {
    const seed = await seedCommunity({ rules: [] as never[] });
    const rules = await repo.findByWorkflow(seed.workflowId!);
    expect(rules).toEqual([]);
  });
});

describe('ThresholdRepository', { tags: ['integration'] }, () => {
  const repo = new ThresholdRepository(logger);

  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('resolve retourne le seuil personnalisé s’il existe (calibration medium=0.25, high=0.70)', async () => {
    const seed = await seedCommunity({
      thresholds: [
        { riskClass: 'TOXICITY', medium: 0.25, high: 0.7, critical: 0.9 },
      ],
    });

    const thresholds = await repo.findByWorkflow(seed.workflowId!);
    const resolved = repo.resolve('TOXICITY', thresholds);
    expect(resolved).toMatchObject({ low: 0.25, medium: 0.25, high: 0.7, critical: 0.9 });
  });

  it('resolve retombe sur les défauts 0.25/0.50/0.75/1.00 si seuil absent', async () => {
    const seed = await seedCommunity({
      thresholds: [],
    });

    const thresholds = await repo.findByWorkflow(seed.workflowId!);
    const resolved = repo.resolve('TOXICITY', thresholds);
    expect(resolved).toMatchObject({ low: 0.25, medium: 0.5, high: 0.75, critical: 1.0 });
  });

  it('resolve retombe sur les défauts si un seuil viole les bornes', async () => {
    const seed = await seedCommunity({
      thresholds: [{ riskClass: 'TOXICITY', low: 0.9, medium: 0.2 }],
    });

    const thresholds = await repo.findByWorkflow(seed.workflowId!);
    const resolved = repo.resolve('TOXICITY', thresholds);
    expect(resolved).toMatchObject({ low: 0.25, medium: 0.5, high: 0.75, critical: 1.0 });
  });
});