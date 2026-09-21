/**
 * Validator — validation de forme du payload webhook entrant.
 *
 * Décision actée : le payload accepté est un batch `{ items: [...] }`
 * (cf. `.agent/phase-02/main.md` §8, point ouvert tranché). Chaque item
 * correspond au contenu de la spec fonctionnelle §6.2 aplati :
 * `{ contentId, contentType, userRef, timestamp, data: { text, attachments } }`.
 *
 * Aucun appel réseau ni base de données : validation pure de structure.
 * Lève une `ValidationError` listant les champs en cause.
 */

import { ValidationError } from '../types/errors.js';
import { AttachmentType, ContentType } from '../types/job.js';
import type { IncomingContent, WebhookPayload } from '../types/payload.js';

export interface ValidatorOptions {
  /** Nombre maximal d'items acceptés par payload (défaut 1000). */
  maxItemsPerBatch: number;
}

const CONTENT_TYPES = new Set<string>(Object.values(ContentType));
const ATTACHMENT_TYPES = new Set<string>(Object.values(AttachmentType));

export class Validator {
  constructor(private readonly options: ValidatorOptions) {}

  /**
   * Valide et normalise le payload. Retourne le payload typé si valide,
   * lève une `ValidationError` (avec la liste des champs fautifs) sinon.
   */
  validate(payload: unknown): WebhookPayload {
    if (!isObject(payload)) {
      throw new ValidationError('payload must be an object', ['payload']);
    }

    if (!Array.isArray(payload.items)) {
      throw new ValidationError('payload.items is required and must be an array', ['items']);
    }

    if (payload.items.length === 0) {
      throw new ValidationError('payload.items must not be empty', ['items']);
    }

    if (payload.items.length > this.options.maxItemsPerBatch) {
      throw new ValidationError(
        `payload.items exceeds maximum of ${this.options.maxItemsPerBatch}`,
        ['items']
      );
    }

    const seenContentIds = new Set<string>();

    payload.items.forEach((item: unknown, index: number) => {
      this.validateItem(item, index, seenContentIds);
    });

    return payload as unknown as WebhookPayload;
  }

  private validateItem(item: unknown, index: number, seenContentIds: Set<string>): void {
    const prefix = `items[${index}]`;
    if (!isObject(item)) {
      throw new ValidationError(`${prefix} must be an object`, [prefix]);
    }

    if (typeof item.contentId !== 'string' || item.contentId.length === 0) {
      throw new ValidationError(`${prefix}.contentId is required and must be a non-empty string`, [
        `${prefix}.contentId`,
      ]);
    }

    // Décision de validité alignée sur phase 3 : contentId uniques dans le lot.
    if (seenContentIds.has(item.contentId)) {
      throw new ValidationError(`${prefix}.contentId must be unique within the batch`, [
        `${prefix}.contentId`,
      ]);
    }
    seenContentIds.add(item.contentId);

    if (typeof item.contentType !== 'string' || !CONTENT_TYPES.has(item.contentType)) {
      throw new ValidationError(`${prefix}.contentType is invalid`, [`${prefix}.contentType`]);
    }

    if (typeof item.userRef !== 'string' || item.userRef.length === 0) {
      throw new ValidationError(`${prefix}.userRef is required and must be a non-empty string`, [
        `${prefix}.userRef`,
      ]);
    }

    if (typeof item.timestamp !== 'string' || Number.isNaN(Date.parse(item.timestamp))) {
      throw new ValidationError(`${prefix}.timestamp must be a valid ISO-8601 string`, [
        `${prefix}.timestamp`,
      ]);
    }

    if (!isObject(item.data)) {
      throw new ValidationError(`${prefix}.data is required`, [`${prefix}.data`]);
    }

    const text = item.data.text;
    if (text !== null && typeof text !== 'string') {
      throw new ValidationError(`${prefix}.data.text must be a string or null`, [
        `${prefix}.data.text`,
      ]);
    }

    if (!Array.isArray(item.data.attachments)) {
      throw new ValidationError(`${prefix}.data.attachments must be an array`, [
        `${prefix}.data.attachments`,
      ]);
    }

    item.data.attachments.forEach((attachment: unknown, attIndex: number) => {
      const attPrefix = `${prefix}.data.attachments[${attIndex}]`;
      if (!isObject(attachment)) {
        throw new ValidationError(`${attPrefix} must be an object`, [attPrefix]);
      }
      if (typeof attachment.type !== 'string' || !ATTACHMENT_TYPES.has(attachment.type)) {
        throw new ValidationError(`${attPrefix}.type is invalid`, [`${attPrefix}.type`]);
      }
      if (typeof attachment.url !== 'string' || attachment.url.length === 0) {
        throw new ValidationError(`${attPrefix}.url is required and must be a non-empty string`, [
          `${attPrefix}.url`,
        ]);
      }
    });

    // text et attachments ne peuvent pas être tous deux vides.
    const hasText = typeof text === 'string' && text.length > 0;
    const hasAttachments = item.data.attachments.length > 0;
    if (!hasText && !hasAttachments) {
      throw new ValidationError(`${prefix} must contain text or at least one attachment`, [
        `${prefix}.data.text`,
        `${prefix}.data.attachments`,
      ]);
    }
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}