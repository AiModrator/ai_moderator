/**
 * Actions résultant de la résolution `(classe, sévérité) → règles`.
 */

import type { ContentAction, UserAction } from '@ai-moderator/database';

export interface ActionsResult {
  contentActions: ContentAction[];
  userActions: UserAction[];
}

export const EMPTY_ACTIONS: ActionsResult = Object.freeze({
  contentActions: [],
  userActions: [],
});