/**
 * Tâche 08 — Validator (validation de forme du payload webhook).
 * Tests unitaires : aucune dépendance externe.
 */

import { describe, it, expect } from 'vitest';
import { Validator } from '../../src/core/Validator.js';
import { ValidationError } from '../../src/types/errors.js';
import { ContentType } from '../../src/types/job.js';
import { AttachmentType } from '../../src/types/job.js';
import { makeItem, makePayload } from '../utils/payload.js';

const validator = new Validator({ maxItemsPerBatch: 10 });

function expectValidationError(payload: unknown, field: string): void {
  try {
    validator.validate(payload);
    throw new Error('expected validate() to throw');
  } catch (error) {
    expect(error).toBeInstanceOf(ValidationError);
    expect((error as ValidationError).fields).toContain(field);
  }
}

describe('Validator', { tags: ['unit'] }, () => {
  it('payload valide (batch de 1) → retourne le payload typé', () => {
    const payload = makePayload([makeItem()]);
    expect(validator.validate(payload)).toBe(payload);
  });

  it('payload multi-items valide → accepté', () => {
    const payload = makePayload([
      makeItem({ contentId: 'a' }),
      makeItem({ contentId: 'b' }),
      makeItem({ contentId: 'c' }),
    ]);
    expect(validator.validate(payload)).toBe(payload);
  });

  it('payload non-objet → rejeté sur le champ payload', () => {
    expectValidationError('not-an-object', 'payload');
    expectValidationError(null, 'payload');
  });

  it('items absent → rejeté sur le champ items', () => {
    expectValidationError({}, 'items');
  });

  it('items vide → rejeté sur le champ items', () => {
    expectValidationError({ items: [] }, 'items');
  });

  it('items dépasse maxItemsPerBatch → rejeté sur le champ items', () => {
    const items = Array.from({ length: 11 }, (_, i) => makeItem({ contentId: `c-${i}` }));
    expectValidationError({ items }, 'items');
  });

  it('item non-objet → rejeté sur items[0]', () => {
    expectValidationError({ items: ['nope'] }, 'items[0]');
  });

  it('contentId manquant → rejeté sur items[0].contentId', () => {
    const item = makeItem();
    delete (item as Record<string, unknown>)['contentId'];
    expectValidationError({ items: [item] }, 'items[0].contentId');
  });

  it('contentId dupliqué dans le lot → rejeté', () => {
    expectValidationError(
      { items: [makeItem({ contentId: 'dup' }), makeItem({ contentId: 'dup' })] },
      'items[1].contentId'
    );
  });

  it('contentType invalide → rejeté sur items[0].contentType', () => {
    expectValidationError(
      { items: [{ ...makeItem(), contentType: 'invalid_type' }] },
      'items[0].contentType'
    );
  });

  it('userRef manquant → rejeté sur items[0].userRef', () => {
    const item = makeItem();
    delete (item as Record<string, unknown>)['userRef'];
    expectValidationError({ items: [item] }, 'items[0].userRef');
  });

  it('timestamp invalide → rejeté sur items[0].timestamp', () => {
    expectValidationError(
      { items: [makeItem({ timestamp: 'not-a-date' })] },
      'items[0].timestamp'
    );
  });

  it('data.text non-string et non-null → rejeté sur items[0].data.text', () => {
    expectValidationError(
      { items: [{ ...makeItem(), data: { text: 123, attachments: [] } }] },
      'items[0].data.text'
    );
  });

  it('attachments non-tableau → rejeté sur items[0].data.attachments', () => {
    expectValidationError(
      { items: [{ ...makeItem(), data: { text: 'hi', attachments: 'nope' } }] },
      'items[0].data.attachments'
    );
  });

  it('attachment.type invalide → rejeté', () => {
    expectValidationError(
      {
        items: [
          makeItem({
            attachments: [{ type: 'invalid' as AttachmentType, url: 'https://x' }],
          }),
        ],
      },
      'items[0].data.attachments[0].type'
    );
  });

  it('attachment.url manquante → rejeté', () => {
    expectValidationError(
      {
        items: [
          makeItem({
            attachments: [{ type: AttachmentType.IMAGE, url: '' }],
          }),
        ],
      },
      'items[0].data.attachments[0].url'
    );
  });

  it('text vide et aucun attachment → rejeté sur text/attachments', () => {
    expectValidationError(
      { items: [makeItem({ text: '', attachments: [] })] },
      'items[0].data.text'
    );
  });

  it('text null mais attachment présent → accepté', () => {
    const payload = makePayload([
      makeItem({
        text: null,
        contentType: ContentType.ATTACHMENT_ONLY,
        attachments: [{ type: AttachmentType.IMAGE, url: 'https://example.com/img.png' }],
      }),
    ]);
    expect(validator.validate(payload)).toBe(payload);
  });
});