/**
 * Utilitaires données de test : payloads webhook valides et items.
 */

import type { IncomingContent, WebhookPayload } from '../../src/types/payload.js';
import { AttachmentType, ContentType } from '../../src/types/job.js';

export interface MakeItemOverrides {
  contentId?: string;
  contentType?: ContentType;
  userRef?: string;
  timestamp?: string;
  text?: string | null;
  attachments?: Array<{ type: AttachmentType; url: string }>;
}

export function makeItem(overrides: MakeItemOverrides = {}): IncomingContent {
  return {
    contentId: overrides.contentId ?? `content-${Math.random().toString(36).slice(2, 10)}`,
    contentType: overrides.contentType ?? ContentType.MESSAGE,
    userRef: overrides.userRef ?? 'user-123',
    timestamp: overrides.timestamp ?? '2026-09-21T12:00:00.000Z',
    data: {
      text: overrides.text !== undefined ? overrides.text : 'Hello world',
      attachments: overrides.attachments ?? [],
    },
  };
}

export function makePayload(items: IncomingContent[] = [makeItem()]): WebhookPayload {
  return { items };
}