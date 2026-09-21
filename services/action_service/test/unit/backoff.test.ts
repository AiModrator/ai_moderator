/**
 * Tâche 06 — Backoff exponentiel plafonné (`delayFor`).
 */

import { describe, expect, it } from 'vitest';
import { delayFor, sleep, delaySequence } from '../../src/utils/backoff.js';

describe('backoff', { tags: ['unit'] }, () => {
  it('séquence exponentielle de base : 1000 → 2000 → 4000 → 8000 → 16000', () => {
    expect(delaySequence(1000, 30000, 5)).toEqual([1000, 2000, 4000, 8000, 16000]);
  });

  it('premier délai = base (attempt 0-based)', () => {
    expect(delayFor(1, 1000, 30000)).toBe(1000);
  });

  it('plafonnement : jamais au-delà de maxDelay', () => {
    expect(delayFor(6, 1000, 30000)).toBe(30000);
    expect(delayFor(10, 1000, 30000)).toBe(30000);
    expect(delaySequence(1000, 1280, 10)).toEqual([1000, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280]);
  });

  it('base non-standard, séquence plafonnée', () => {
    expect(delaySequence(2500, 20000, 5)).toEqual([2500, 5000, 10000, 20000, 20000]);
  });

  it('suite strictement croissante puis plate après plafond', () => {
    const seq = delaySequence(100, 5000, 12);
    for (let i = 1; i < seq.length; i += 1) {
      expect(seq[i]).toBeGreaterThanOrEqual(seq[i - 1]);
    }
    expect(seq.at(-1)).toBe(5000);
  });

  it('sleep attend ~ms demandées', async () => {
    const start = Date.now();
    await sleep(30);
    expect(Date.now() - start).toBeGreaterThanOrEqual(25);
  });
});