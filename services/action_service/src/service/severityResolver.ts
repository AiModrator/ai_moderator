/**
 * SeverityResolver — logique pure : mapping `score → sévérité` via le profil
 * de seuils (D-04, `Threshold`). Utilise des bandes semi-ouvertes :
 *
 *   [0, low)          → NONE
 *   [low, medium)     → LOW
 *   [medium, high)    → MEDIUM
 *   [high, critical)  → HIGH
 *   [critical, 1]     → CRITICAL
 *
 * Bornes exactes : `score == medium` → MEDIUM, `score == high` → HIGH, etc.
 */

import type { Severity } from '../types/severity.js';
import type { ThresholdProfile } from '../types/threshold.js';

export class SeverityResolver {
  resolve(score: number, threshold: Pick<ThresholdProfile, 'low' | 'medium' | 'high' | 'critical'>): Severity {
    if (score < threshold.low) return 'NONE';
    if (score < threshold.medium) return 'LOW';
    if (score < threshold.high) return 'MEDIUM';
    if (score < threshold.critical) return 'HIGH';
    return 'CRITICAL';
  }
}