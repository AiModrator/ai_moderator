/**
 * Modèle de données D-02 (MongoDB — historique).
 * Base `ai_moderator_history`. Collection `moderation_cases` et `user_actions`.
 */

import type { ContentAction, RiskClass, UserAction } from '@ai-moderator/database';
import type { Decision, VerdictDetection, VerdictStatus } from './verdict.js';
import type { FilterStatus } from './job.js';

export const MODERATION_CASES_COLLECTION = 'moderation_cases';
export const USER_ACTIONS_COLLECTION = 'user_actions';

export type CallbackStatus = 'pending' | 'delivered' | 'failed';

export interface CallbackInfo {
  url: string;
  status: CallbackStatus;
  attempts: number;
  lastError: string | null;
  deliveredAt: Date | null;
}

export interface FiltersReport {
  filter: string;
  status: FilterStatus;
  attempts: number;
  error: string | null;
}

export interface ModerationCase {
  moderationCaseId: string;
  communityRef: string;
  accountId: string;
  contentId: string;
  contentType: string;
  userRef: string;
  contentTimestamp: Date;
  detections: VerdictDetection[];
  status: VerdictStatus;
  decision: Decision;
  contentActions: ContentAction[];
  userActions: UserAction[];
  needsReview: boolean;
  filtersReport: FiltersReport[];
  callback: CallbackInfo;
  createdAt: Date;
  updatedAt: Date;
}

export interface UserActionRecord {
  communityRef: string;
  userRef: string;
  action: UserAction;
  riskClass: RiskClass;
  severity: string;
  moderationCaseId: string;
  createdAt: Date;
}