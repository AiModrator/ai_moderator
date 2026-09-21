/**
 * ThresholdRepository — seuils de sévérité par classe (D-04, modèle `Threshold`).
 * Repli par défaut (0.25/0.50/0.75/1.00) si aucun seuil n'existe pour la classe,
 * ou si un seuil stocké viole la contrainte de bornes (`0 ≤ low ≤ … ≤ critical ≤ 1`).
 */

import type { RiskClass, Threshold } from '@ai-moderator/database';
import type { ThresholdProfile } from '../types/threshold.js';
import { DEFAULT_THRESHOLDS, isOrderedThreshold } from '../types/threshold.js';
import { ConfigReadError } from '../exceptions/index.js';
import { prismaClient } from '../config/prisma.js';
import type { Logger } from '../utils/logger.js';

export class ThresholdRepository {
  constructor(private readonly logger: Logger) {}

  async findByWorkflow(workflowId: string): Promise<Threshold[]> {
    try {
      return await prismaClient.threshold.findMany({ where: { workflowId } });
    } catch (error) {
      this.logger.error('D-04 read failed (thresholds)', { workflowId, err: error });
      throw new ConfigReadError(`failed to read thresholds for workflow ${workflowId}`);
    }
  }

  /**
   * Profil de seuils pour une classe. Repli sur les défauts si la classe est
   * absente (log warning, décision D7) ou si les bornes sont incohérentes.
   */
  resolve(riskClass: RiskClass, thresholds: Threshold[]): ThresholdProfile {
    if (thresholds.length === 0) {
      this.logger.warn('threshold not found, using defaults', { riskClass });
      return { ...DEFAULT_THRESHOLDS, riskClass };
    }

    const match = thresholds.find((t) => t.riskClass === riskClass);
    if (!match) {
      this.logger.warn('threshold not found, using defaults', { riskClass });
      return { ...DEFAULT_THRESHOLDS, riskClass };
    }

    const profile: ThresholdProfile = {
      workflowId: match.workflowId,
      riskClass: match.riskClass,
      low: match.low,
      medium: match.medium,
      high: match.high,
      critical: match.critical,
    };

    if (!isOrderedThreshold(profile)) {
      this.logger.warn('threshold violates bounds, using defaults', {
        riskClass,
        low: profile.low,
        medium: profile.medium,
        high: profile.high,
        critical: profile.critical,
      });
      return { ...DEFAULT_THRESHOLDS, riskClass };
    }

    return profile;
  }
}