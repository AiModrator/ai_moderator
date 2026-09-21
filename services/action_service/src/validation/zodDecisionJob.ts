/**
 * Validation du job `decisionQueue` (contrat `phase-05/main.md` §2).
 * Une non-conformité → `InvalidJobError` (job `failed`, pas de retry).
 */

import { z } from 'zod';
import { RiskClass } from '@ai-moderator/database';
import type { DecisionJob } from '../types/job.js';

const riskClassOptions = Object.values(RiskClass) as unknown as [string, ...string[]];

const jobStatus = z.enum(['COMPLETE', 'PARTIAL']);
const filterStatus = z.enum(['COMPLETED', 'FAILED', 'UNAVAILABLE']);

const evidence = z.object({
  filter: z.string().min(1),
  score: z.number().min(0).max(1),
  source: z.string().min(1),
  detail: z.string().optional(),
});

const detection = z.object({
  class: z.enum(riskClassOptions),
  score: z.number().min(0).max(1),
  sources: z.array(z.string().min(1)).min(1),
  evidence: z.array(evidence),
});

const filtersReportEntry = z.object({
  filter: z.string().min(1),
  status: filterStatus,
  attempts: z.number().int().min(1),
  error: z.string().nullable(),
});

export const zodDecisionJob = z.object({
  batchId: z.string().min(1),
  communityRef: z.string().min(1),
  content: z.object({
    contentId: z.string().min(1),
    contentType: z.string().min(1),
    userRef: z.string().min(1),
    timestamp: z.string().min(1),
  }),
  activeClasses: z.array(z.enum(riskClassOptions)).min(1),
  status: jobStatus,
  detections: z.array(detection),
  filtersReport: z.array(filtersReportEntry),
  moderatedAt: z.string().min(1),
  processingMs: z.number().int().min(0),
});

export type ZodDecisionJob = z.infer<typeof zodDecisionJob>;

/** Valide et retourne le job typé. Lève `ZodError` en cas de non-conformité. */
export function parseDecisionJob(input: unknown): DecisionJob {
  return zodDecisionJob.parse(input) as DecisionJob;
}