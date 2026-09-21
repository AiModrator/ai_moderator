/**
 * Contrats de données inter-services de l'Ingestion Service.
 * `ContentBatchJob` : contrat de sortie vers `contentQueue`
 * — doit correspondre EXACTEMENT à l'entrée consommée par le Moderation Service
 * (`.agent/phase-03/main.md` §3.2).
 */

import type { RiskClass } from '@ai-moderator/database';

export type { RiskClass };

export enum ContentType {
  POST = 'post',
  COMMENT = 'comment',
  MESSAGE = 'message',
  PROFILE_BIO = 'profile_bio',
  ATTACHMENT_ONLY = 'attachment_only',
}

export enum AttachmentType {
  IMAGE = 'image',
  VIDEO = 'video',
}

export interface Attachment {
  type: AttachmentType;
  url: string;
}

/**
 * Un item de contenu tel que transmis au Moderation Service.
 */
export interface ContentItem {
  contentId: string;
  contentType: ContentType;
  userRef: string;
  timestamp: string; // ISO-8601
  text: string | null;
  attachments: Attachment[];
}

/**
 * Job `contentQueue` — contrat Ingestion → Moderation.
 * Nom de job BullMQ : `moderateBatch`. Options : `attempts: 1`, `removeOnComplete: true`.
 */
export interface ContentBatchJob {
  batchId: string;
  communityRef: string;
  activeClasses: RiskClass[];
  items: ContentItem[];
  retryState: null; // toujours null au premier passage
}