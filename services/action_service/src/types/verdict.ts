/**
 * Verdict produit par le `DecisionProcessor` — agrégation des actions,
 * alimente l'historique D-02 et le callback client.
 */

import type { ContentAction, RiskClass, UserAction } from '@ai-moderator/database';
import type { Severity } from './severity.js';

export type VerdictStatus = 'completed' | 'pending_review';
export type Decision = 'allow' | 'action_taken';

export interface VerdictDetection {
  class: RiskClass;
  score: number;
  severity: Severity;
  sources: string[];
}

export interface Verdict {
  moderationCaseId: string;
  contentId: string;
  communityRef: string;
  userRef: string;
  contentType: string;
  status: VerdictStatus;
  decision: Decision;
  detections: VerdictDetection[];
  contentActions: ContentAction[];
  userActions: UserAction[];
  needsReview: boolean;
}