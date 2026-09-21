import { AttachmentType, ContentType } from './job.js';

/**
 * Payload webhook entrant — décision : format `items[]` (batch).
 * Conforme à la spec fonctionnelle §6.2, adapté pour accepter plusieurs
 * contenus en un seul appel webhook.
 */
export interface IncomingContent {
  contentId: string;
  contentType: ContentType;
  userRef: string;
  timestamp: string; // ISO-8601
  data: {
    text: string | null;
    attachments: Array<{ type: AttachmentType; url: string }>;
  };
}

export interface WebhookPayload {
  items: IncomingContent[];
}