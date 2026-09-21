/**
 * Identifiants déterministes : `moderationCaseId = uuid.v5("batchId:contentId")`.
 * Un re-jeu du job écrase le même cas — jamais de doublon (décision D6).
 */

import { v5 as uuidv5 } from 'uuid';

/** Namespace fixe du projet (UUID v5). */
export const MODERATION_NAMESPACE = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';

export function moderationCaseId(batchId: string, contentId: string): string {
  return uuidv5(`${batchId}:${contentId}`, MODERATION_NAMESPACE);
}