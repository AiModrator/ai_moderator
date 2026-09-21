/**
 * Tâche 06 — CallbackClient : livraison HTTP avec retry/backoff.
 * Tests d'intégration sur serveur HTTP de test (succès, retry, 4xx, épuisement).
 */

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Verdict } from '../../src/types/verdict.js';
import { CallbackClient, type DeliveryResult } from '../../src/service/callbackClient.js';
import { Logger } from '../../src/utils/logger.js';
import { TestCallbackServer } from '../utils/callbackServer.js';

const logger = Logger.create('silent');

function makeVerdict(overrides: Partial<Verdict> = {}): Verdict {
  return {
    moderationCaseId: 'case-1',
    contentId: 'post-42',
    communityRef: 'community-1',
    userRef: 'user-7',
    contentType: 'post',
    status: 'completed',
    decision: 'action_taken',
    detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] }],
    contentActions: ['DELETE_POST'],
    userActions: ['TIMEOUT_USER'],
    needsReview: false,
    ...overrides,
  };
}

function client(overrides: Partial<import('../../src/service/callbackClient.js').CallbackClientConfig> = {}): CallbackClient {
  return new CallbackClient(
    { timeoutMs: 2000, maxAttempts: 5, baseDelayMs: 1000, maxDelayMs: 30000, ...overrides },
    logger
  );
}

describe('CallbackClient', { tags: ['integration'] }, () => {
  let server: TestCallbackServer;
  let baseUrl: string;

  beforeAll(async () => {
    server = new TestCallbackServer();
    baseUrl = `http://127.0.0.1:${await server.listen()}`;
  });

  afterAll(async () => {
    await server.close();
  });

  it('2xx → delivered en 1 essai, corps = verdict sans needsReview', async () => {
    server.queue([{ status: 200 }]);
    const result = await client().deliver(`${baseUrl}/cb`, makeVerdict());

    expect(result.status).toBe('delivered');
    expect(result.attempts).toBe(1);
    expect(result.lastError).toBeNull();
    expect(result.deliveredAt).not.toBeNull();
    expect(server.callCount).toBe(1);
    expect(server.lastBody).toEqual({
      moderationCaseId: 'case-1',
      contentId: 'post-42',
      status: 'completed',
      decision: 'action_taken',
      detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] }],
      contentActions: ['DELETE_POST'],
      userActions: ['TIMEOUT_USER'],
    });
    expect(server.lastHeaders['content-type']).toContain('application/json');
  });

  it('503 puis 200 → delivered au 2ᵉ essai (compteur d’appels = 2)', async () => {
    const c = client({ baseDelayMs: 5, maxDelayMs: 5 });
    server.queue([{ status: 503 }, { status: 200 }]);

    const before = server.callCount;
    const result = await c.deliver(`${baseUrl}/cb`, makeVerdict());

    expect(result.status).toBe('delivered');
    expect(result.attempts).toBe(2);
    expect(server.callCount - before).toBe(2);
  });

  it('429 → retry puis 201 → delivered', async () => {
    const c = client({ baseDelayMs: 5, maxDelayMs: 5 });
    server.queue([{ status: 429 }, { status: 201 }]);

    const result = await c.deliver(`${baseUrl}/cb`, makeVerdict());
    expect(result.status).toBe('delivered');
    expect(result.attempts).toBe(2);
  });

  it('400 → failed immédiat (aucun retry)', async () => {
    const c = client({ baseDelayMs: 1_000_000, maxDelayMs: 1_000_000 });
    server.queue([{ status: 400 }]);

    const before = server.callCount;
    const result = await c.deliver(`${baseUrl}/cb`, makeVerdict());

    expect(result.status).toBe('failed');
    expect(result.attempts).toBe(1);
    expect(result.lastError).toBe('HTTP 400');
    expect(result.deliveredAt).toBeNull();
    expect(server.callCount - before).toBe(1);
  });

  it('timeouts répétés → failed après CALLBACK_MAX_ATTEMPTS, délais exponentiels respectés', async () => {
    const c = client({ timeoutMs: 60, maxAttempts: 3, baseDelayMs: 20, maxDelayMs: 1000 });
    server.queue([{ hang: true, status: 200 }, { hang: true, status: 200 }, { hang: true, status: 200 }]);

    const before = server.callCount;
    const start = Date.now();
    const result = await c.deliver(`${baseUrl}/cb`, makeVerdict());
    const elapsed = Date.now() - start;

    expect(result.status).toBe('failed');
    expect(result.attempts).toBe(3);
    expect(result.lastError).not.toBeNull();
    expect(result.deliveredAt).toBeNull();
    expect(server.callCount - before).toBe(3);
    // délais : 20ms puis 40ms, + 3 timeouts de 60ms → borne basse 20+40=60ms
    expect(elapsed).toBeGreaterThanOrEqual(60);
  });

  it('5xx persistants → failed, aucune livraison (jamais 2xx)', async () => {
    const c = client({ baseDelayMs: 5, maxDelayMs: 5, maxAttempts: 2 });
    server.queue([{ status: 500 }, { status: 502 }]);

    const result = await c.deliver(`${baseUrl}/cb`, makeVerdict());

    expect(result.status).toBe('failed');
    expect(result.attempts).toBe(2);
    expect(result.lastError).toMatch(/^HTTP 5/);
  });
});