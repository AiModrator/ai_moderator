/**
 * Contrat d'entrée — job `decisionQueue`.
 * Aligné sur `phase-03/main.md` §3.4 et `.agent/phase-05/main.md` §2.
 * Aucune sévérité : le mapping score → sévérité est ici et uniquement ici.
 */

import type { RiskClass } from '@ai-moderator/database';

export type JobStatus = 'COMPLETE' | 'PARTIAL';

export interface DecisionEvidence {
  filter: string;
  score: number;
  source: string;
  detail?: string;
}

export interface DecisionDetection {
  class: RiskClass;
  score: number;
  sources: string[];
  evidence: DecisionEvidence[];
}

export type FilterStatus = 'COMPLETED' | 'FAILED' | 'UNAVAILABLE';

export interface FiltersReportEntry {
  filter: string;
  status: FilterStatus;
  attempts: number;
  error: string | null;
}

export interface ContentRef {
  contentId: string;
  contentType: string;
  userRef: string;
  timestamp: string;
}

export interface DecisionJob {
  batchId: string;
  communityRef: string;
  content: ContentRef;
  activeClasses: RiskClass[];
  status: JobStatus;
  detections: DecisionDetection[];
  filtersReport: FiltersReportEntry[];
  moderatedAt: string;
  processingMs: number;
}