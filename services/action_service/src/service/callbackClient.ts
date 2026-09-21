/**
 * CallbackClient — livraison du verdict au `Community.callbackUrl` (D-04).
 * POST JSON, timeout, retry/backoff exponentiel :
 *   - retry sur timeout / 5xx / 429 ;
 *   - pas de retry sur 4xx (permanent failure) ;
 *   - épuisement après `CALLBACK_MAX_ATTEMPTS` → `failed`.
 * Le corps envoyé = verdict (§5) sans `needsReview` (retro-compatible §7.1).
 */

import axios from 'axios';
import type { CallbackPayload, Verdict } from '../types/verdict.js';
import { toCallbackPayload } from '../types/verdict.js';
import { delayFor, sleep } from '../utils/backoff.js';
import type { Logger } from '../utils/logger.js';

export interface DeliveryResult {
  status: 'delivered' | 'failed';
  attempts: number;
  lastError: string | null;
  deliveredAt: Date | null;
}

export interface CallbackClientConfig {
  timeoutMs: number;
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

export class CallbackClient {
  constructor(
    private readonly config: CallbackClientConfig,
    private readonly logger: Logger
  ) {}

  async deliver(url: string, verdict: Verdict): Promise<DeliveryResult> {
    const payload: CallbackPayload = toCallbackPayload(verdict);
    let lastError: string | null = null;

    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt += 1) {
      const outcome = await this.tryOnce(url, payload, attempt);
      if (outcome.done) return outcome.result;

      lastError = outcome.error;
      if (attempt < this.config.maxAttempts) {
        const delay = delayFor(attempt, this.config.baseDelayMs, this.config.maxDelayMs);
        this.logger.warn('callback.retry', { url, attempt, lastError, delayMs: delay });
        await sleep(delay);
      }
    }

    return { status: 'failed', attempts: this.config.maxAttempts, lastError, deliveredAt: null };
  }

  private async tryOnce(
    url: string,
    payload: CallbackPayload,
    attempt: number
  ): Promise<{ done: true; result: DeliveryResult } | { done: false; error: string | null }> {
    try {
      const response = await axios.post(url, payload, {
        timeout: this.config.timeoutMs,
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.status >= 200 && response.status < 300) {
        this.logger.info('callback.delivered', { url, attempts: attempt, statusCode: response.status });
        return { done: true, result: { status: 'delivered', attempts: attempt, lastError: null, deliveredAt: new Date() } };
      }

      const error = `HTTP ${response.status}`;
      const retriable = response.status === 429 || response.status >= 500;
      this.logger.warn('callback.attempt', { url, attempts: attempt, lastError: error });
      if (!retriable) {
        return { done: true, result: { status: 'failed', attempts: attempt, lastError: error, deliveredAt: null } };
      }
      return { done: false, error };
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined;
      const message = error instanceof Error ? error.message : String(error);
      const label = status !== undefined ? `HTTP ${status}` : message;

      // Axios rejette tout statut non-2xx : statuts gérés ici.
      // Permanent → 4xx (sauf 429, retriable). Retriable → 5xx, 429, timeout/réseau.
      const permanent = status !== undefined && status !== 429 && status >= 400 && status < 500;
      if (permanent) {
        this.logger.warn('callback.attempt', { url, attempts: attempt, lastError: label });
        return { done: true, result: { status: 'failed', attempts: attempt, lastError: label, deliveredAt: null } };
      }

      this.logger.warn('callback.attempt', { url, attempts: attempt, lastError: label });
      return { done: false, error: label };
    }
  }
}