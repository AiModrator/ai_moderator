/**
 * Tâche 05 — DecisionProcessor (orchestration du verdict).
 * Tests d'intégration : D-04 réel (seed communautés + workflow + règles + seuils).
 */

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { ContentAction, Severity, UserAction } from '@ai-moderator/database';
import { DecisionProcessor } from '../../src/service/decisionProcessor.js';
import { SeverityResolver } from '../../src/service/severityResolver.js';
import { ActionResolver } from '../../src/service/actionResolver.js';
import { CommunityRepository } from '../../src/models/communityRepository.js';
import { RuleRepository } from '../../src/models/ruleRepository.js';
import { ThresholdRepository } from '../../src/models/thresholdRepository.js';
import { Logger } from '../../src/utils/logger.js';
import { moderationCaseId } from '../../src/utils/id.js';
import { resetDatabase, seedCommunity, disconnectDatabase } from '../utils/database.js';
import { makeDecisionJob } from '../utils/job.js';
import type { DecisionJob } from '../../src/types/job.js';

const logger = Logger.create('silent');

function buildProcessor(): DecisionProcessor {
  const ctx = {
    communityRepository: new CommunityRepository(logger),
    ruleRepository: new RuleRepository(logger),
    thresholdRepository: new ThresholdRepository(logger),
    severityResolver: new SeverityResolver(),
    actionResolver: new ActionResolver(),
    logger,
  };
  return new DecisionProcessor(ctx);
}

describe('DecisionProcessor', { tags: ['integration'] }, () => {
  beforeAll(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await disconnectDatabase();
  });

  it('COMPLETE sans détection → decision=allow, aucune action, detections vides', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });
    const job = makeDecisionJob({ communityRef: seed.communityId });

    const verdict = await buildProcessor().process(job);
    expect(verdict.decision).toBe('allow');
    expect(verdict.contentActions).toEqual([]);
    expect(verdict.userActions).toEqual([]);
    expect(verdict.detections).toEqual([]);
    expect(verdict.status).toBe('completed');
    expect(verdict.needsReview).toBe(false);
  });

  it('TOXICITY 0.91 + seuil défaut → HIGH → DELETE_POST + TIMEOUT_USER', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [
        { class: 'TOXICITY', score: 0.91, sources: ['text'], evidence: [] },
      ],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.decision).toBe('action_taken');
    expect(verdict.contentActions).toEqual(['DELETE_POST']);
    expect(verdict.userActions).toEqual(['TIMEOUT_USER']);
    expect(verdict.detections).toEqual([
      { class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] },
    ]);
  });

  it('PARTIAL → needsReview + pending_review + FLAG_FOR_REVIEW', async () => {
    const seed = await seedCommunity({
      rules: [],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      status: 'PARTIAL',
      filtersReport: [{ filter: 'TextAIFilter', status: 'UNAVAILABLE', attempts: 1, error: 'provider down' }],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.status).toBe('pending_review');
    expect(verdict.needsReview).toBe(true);
    expect(verdict.contentActions).toContain('FLAG_FOR_REVIEW');
    expect(verdict.decision).toBe('action_taken');
  });

  it('déterminisme : même batchId:contentId → même moderationCaseId (uuid v5)', async () => {
    const seed = await seedCommunity({ rules: [] });
    const job = makeDecisionJob({ communityRef: seed.communityId, batchId: 'batch-x', content: { contentId: 'post-1', contentType: 'post', userRef: 'u', timestamp: 't' } });

    const processor = buildProcessor();
    const v1 = await processor.process(job);
    const v2 = await processor.process({ ...job, processingMs: 999 });

    expect(v1.moderationCaseId).toBe(v2.moderationCaseId);
    expect(v1.moderationCaseId).toBe(moderationCaseId('batch-x', 'post-1'));
  });

  it('score sous low → aucune sévérité ni action (allow)', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [{ class: 'TOXICITY', score: 0.1, sources: ['text'], evidence: [] }],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.decision).toBe('allow');
    expect(verdict.detections).toEqual([]);
    expect(verdict.contentActions).toEqual([]);
  });

  it('calibration personnalisée : critical=0.90 → score 0.95 → CRITICAL → BAN_USER (au lieu de HIGH)', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.CRITICAL, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.BAN_USER] },
      ],
      thresholds: [{ riskClass: 'TOXICITY', critical: 0.9 }],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [{ class: 'TOXICITY', score: 0.95, sources: ['text'], evidence: [] }],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.detections[0]).toMatchObject({ class: 'TOXICITY', score: 0.95, severity: 'CRITICAL' });
    expect(verdict.userActions).toEqual(['BAN_USER']);
  });

  it('calibration personnalisée : low=0.50 → score 0.40 → NONE, aucune action', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.LOW, contentActions: [ContentAction.HIDE_POST], userActions: [UserAction.WARN_USER] },
      ],
      thresholds: [{ riskClass: 'TOXICITY', low: 0.5 }],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [{ class: 'TOXICITY', score: 0.4, sources: ['text'], evidence: [] }],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.decision).toBe('allow');
    expect(verdict.detections).toEqual([]);
  });

  it('communauté inconnue → CommunityNotFoundError propagée (retry métier interdit)', async () => {
    const job = makeDecisionJob({ communityRef: 'absent-community' });
    await expect(buildProcessor().process(job)).rejects.toThrow(/community not found/);
  });

  it('détection MEDIUM mais règle uniquement HIGH → aucune action, décision allow', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
      ],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [{ class: 'TOXICITY', score: 0.6, sources: ['text'], evidence: [] }],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.detections[0]).toMatchObject({ severity: 'MEDIUM' });
    expect(verdict.decision).toBe('allow');
    expect(verdict.contentActions).toEqual([]);
  });

  it('agrégation dédoublonnée sur plusieurs détections', async () => {
    const seed = await seedCommunity({
      rules: [
        { riskClass: 'TOXICITY', severity: Severity.HIGH, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.TIMEOUT_USER] },
        { riskClass: 'SEXUAL', severity: Severity.CRITICAL, contentActions: [ContentAction.DELETE_POST], userActions: [UserAction.BAN_USER] },
      ],
    });
    const job = makeDecisionJob({
      communityRef: seed.communityId,
      detections: [
        { class: 'TOXICITY', score: 0.91, sources: ['text'], evidence: [] },
        { class: 'SEXUAL', score: 1.0, sources: ['image'], evidence: [] },
      ],
    });

    const verdict = await buildProcessor().process(job);
    expect(verdict.contentActions).toEqual(['DELETE_POST']);
    expect(verdict.userActions).toEqual(['TIMEOUT_USER', 'BAN_USER']);
  });
});