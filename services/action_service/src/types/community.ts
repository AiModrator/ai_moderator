/**
 * Contexte communautaire résolu depuis D-04 (config de décision).
 */

export interface CommunityContext {
  communityId: string;
  accountId: string;
  callbackUrl: string;
  workflowId: string | null;
}