/**
 * Profil de seuils de sévérité par classe (D-04, modèle `Threshold`).
 * Bornes : `0 ≤ low ≤ medium ≤ high ≤ critical ≤ 1`.
 */

import type { RiskClass } from '@ai-moderator/database';

export interface ThresholdProfile {
  workflowId?: string;
  riskClass?: RiskClass;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export const DEFAULT_THRESHOLDS: ThresholdProfile = Object.freeze({
  low: 0.25,
  medium: 0.5,
  high: 0.75,
  critical: 1.0,
});

export function isOrderedThreshold(t: Pick<ThresholdProfile, 'low' | 'medium' | 'high' | 'critical'>): boolean {
  return 0 <= t.low && t.low <= t.medium && t.medium <= t.high && t.high <= t.critical && t.critical <= 1;
}