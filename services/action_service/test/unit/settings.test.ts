/**
 * Tâche 01 — Settings (env typé/validé).
 * Tests unitaires : parsing correct et rejet des configurations incohérentes.
 */

import { describe, it, expect } from 'vitest';
import { Settings } from '../../src/config/settings.js';

const validEnv: Record<string, string> = {
  HTTP_PORT: '3001',
  DATABASE_URL: 'postgresql://postgres:postgres@localhost:5432/ai_moderator',
  DECISION_WORKER_CONCURRENCY: '5',
  DEFAULT_LOW: '0.25',
  DEFAULT_MEDIUM: '0.50',
  DEFAULT_HIGH: '0.75',
  DEFAULT_CRITICAL: '1.00',
};

function settingsFor(env: Record<string, string>): Settings {
  return new Settings(env as NodeJS.ProcessEnv);
}

describe('Settings', { tags: ['unit'] }, () => {
  it('parsifie une configuration valide', () => {
    const s = settingsFor(validEnv);
    expect(s.httpPort).toBe(3001);
    expect(s.decisionWorkerConcurrency).toBe(5);
    expect(s.thresholdDefaults).toEqual({ low: 0.25, medium: 0.5, high: 0.75, critical: 1 });
    expect(s.decisionQueueName).toBe('decisionQueue');
    expect(s.mongodbDb).toBe('ai_moderator_history');
    expect(s.callbackMaxAttempts).toBe(5);
    expect(s.callbackBaseDelayMs).toBe(1000);
  });

  it('applique les valeurs par défaut (senza DATABASE_URL explicite)', () => {
    const s = settingsFor({ ...validEnv });
    expect(s.redisHost).toBe('localhost');
    expect(s.redisPort).toBe(6379);
  });

  it('rejette une config sans DATABASE_URL', () => {
    const { DATABASE_URL: _ignored, ...withoutDb } = validEnv;
    expect(() => settingsFor(withoutDb)).toThrow(/DATABASE_URL/);
  });

  it('rejette un seuil par défaut incohérent (low > medium)', () => {
    const env = { ...validEnv, DEFAULT_LOW: '0.80', DEFAULT_MEDIUM: '0.50' };
    expect(() => settingsFor(env)).toThrow(/DEFAULT thresholds/);
  });

  it('rejette un plafond de backoff inférieur à la base', () => {
    const env = { ...validEnv, CALLBACK_BASE_DELAY_MS: '30000', CALLBACK_MAX_DELAY_MS: '1000' };
    expect(() => settingsFor(env)).toThrow(/CALLBACK_BASE_DELAY_MS/);
  });

  it('rejette un port HTTP non numérique', () => {
    const env = { ...validEnv, HTTP_PORT: 'abc' };
    expect(() => settingsFor(env)).toThrow(/HTTP_PORT/);
  });

  it('rejette un CALLBACK_MAX_ATTEMPTS inférieur à 1', () => {
    const env = { ...validEnv, CALLBACK_MAX_ATTEMPTS: '0' };
    expect(() => settingsFor(env)).toThrow(/CALLBACK_MAX_ATTEMPTS/);
  });
});