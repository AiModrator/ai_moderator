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

/**
 * Corps du callback (§7, spec fonctionnelle §7.1) : verdict sans
 * `needsReview` (ni `filtersReport`, absent du verdict). Rétro-compatible
 * avec la spec (ajouts : `detections[].sources` + `score`).
 */
export interface CallbackPayload {
  moderationCaseId: string;
  contentId: string;
  status: VerdictStatus;
  decision: Decision;
  detections: VerdictDetection[];
  contentActions: ContentAction[];
  userActions: UserAction[];
}

export function toCallbackPayload(verdict: Verdict): CallbackPayload {
  return {
    moderationCaseId: verdict.moderationCaseId,
    contentId: verdict.contentId,
    status: verdict.status,
    decision: verdict.decision,
    detections: verdict.detections,
    contentActions: verdict.contentActions,
    userActions: verdict.userActions,
  };
}