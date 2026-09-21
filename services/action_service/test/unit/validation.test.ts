/**
 * Tâche 01 — Validation du `DecisionJob` (Zod).
 * Tests unitaires : acceptation du cas nominal et rejet des cas invalides.
 */

import { describe, it, expect } from 'vitest';
import { parseDecisionJob, zodDecisionJob } from '../../src/validation/zodDecisionJob.js';
import { makeDecisionJob } from '../utils/job.js';

describe('zodDecisionJob', { tags: ['unit'] }, () => {
  it('accepte un job nominal (sans détection → chemin allow)', () => {
    const job = makeDecisionJob();
    expect(parseDecisionJob(job)).toMatchObject({ batchId: job.batchId, status: 'COMPLETE' });
  });

  it('accepte un job avec détections complètes', () => {
    const job = makeDecisionJob({
      detections: [
        {
          class: 'TOXICITY',
          score: 0.91,
          sources: ['text'],
          evidence: [{ filter: 'TextAIFilter', score: 0.91, source: 'text', detail: 'insulte' }],
        },
      ],
      filtersReport: [{ filter: 'TextAIFilter', status: 'COMPLETED', attempts: 1, error: null }],
    });
    expect(() => parseDecisionJob(job)).not.toThrow();
  });

  it('rejette une détection sans score', () => {
    const job = makeDecisionJob({
      detections: [
        { class: 'TOXICITY', sources: ['text'], evidence: [] } as unknown as never,
      ],
    });
    const result = zodDecisionJob.safeParse(job);
    expect(result.success).toBe(false);
  });

  it('rejette une classe inconnue hors enum RiskClass', () => {
    const job = makeDecisionJob({
      detections: [{ class: 'FAKE_CLASS', score: 0.8, sources: ['text'], evidence: [] }] as never[],
    });
    const result = zodDecisionJob.safeParse(job);
    expect(result.success).toBe(false);
  });

  it('rejette un score hors bornes [0, 1]', () => {
    const job = makeDecisionJob({
      detections: [{ class: 'TOXICITY', score: 1.5, sources: ['text'], evidence: [] }] as never[],
    });
    expect(zodDecisionJob.safeParse(job).success).toBe(false);
  });

  it('rejette un status invalide', () => {
    const job = makeDecisionJob({ status: 'UNKNOWN' as never });
    expect(zodDecisionJob.safeParse(job).success).toBe(false);
  });

  it('rejette des activeClasses vides', () => {
    const job = makeDecisionJob({ activeClasses: [] });
    expect(zodDecisionJob.safeParse(job).success).toBe(false);
  });

  it('rejette une détection sans sources', () => {
    const job = makeDecisionJob({
      detections: [{ class: 'TOXICITY', score: 0.8, sources: [], evidence: [] }] as never[],
    });
    expect(zodDecisionJob.safeParse(job).success).toBe(false);
  });

  it('rejette un batchId vide', () => {
    const job = makeDecisionJob({ batchId: '' });
    expect(zodDecisionJob.safeParse(job).success).toBe(false);
  });
});