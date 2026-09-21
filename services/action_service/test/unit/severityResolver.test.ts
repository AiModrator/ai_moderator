/**
 * Tâche 03 — SeverityResolver (mapping score → sévérité, logique pure).
 */

import { describe, it, expect } from 'vitest';
import { SeverityResolver } from '../../src/service/severityResolver.js';

const resolver = new SeverityResolver();

const defaults = { low: 0.25, medium: 0.5, high: 0.75, critical: 1.0 };

describe('SeverityResolver (seuils par défaut)', { tags: ['unit'] }, () => {
  it('0.10 → NONE', () => {
    expect(resolver.resolve(0.1, defaults)).toBe('NONE');
  });

  it('0.24 → NONE (sous low)', () => {
    expect(resolver.resolve(0.24, defaults)).toBe('NONE');
  });

  it('borne exacte : 0.25 → LOW', () => {
    expect(resolver.resolve(0.25, defaults)).toBe('LOW');
  });

  it('0.49 → LOW', () => {
    expect(resolver.resolve(0.49, defaults)).toBe('LOW');
  });

  it('borne exacte : 0.50 → MEDIUM', () => {
    expect(resolver.resolve(0.5, defaults)).toBe('MEDIUM');
  });

  it('0.74 → MEDIUM', () => {
    expect(resolver.resolve(0.74, defaults)).toBe('MEDIUM');
  });

  it('borne exacte : 0.75 → HIGH', () => {
    expect(resolver.resolve(0.75, defaults)).toBe('HIGH');
  });

  it('0.99 → HIGH', () => {
    expect(resolver.resolve(0.99, defaults)).toBe('HIGH');
  });

  it('borne exacte : 1.00 → CRITICAL', () => {
    expect(resolver.resolve(1.0, defaults)).toBe('CRITICAL');
  });
});

describe('SeverityResolver (calibration utilisateur medium=0.25, high=0.70)', { tags: ['unit'] }, () => {
  const cal = { low: 0.25, medium: 0.25, high: 0.7, critical: 1.0 };

  it('0.24 → NONE (bande LOW vide car low == medium)', () => {
    expect(resolver.resolve(0.24, cal)).toBe('NONE');
  });

  it('0.25 → MEDIUM (bande LOW = [0.25, 0.25) vide)', () => {
    expect(resolver.resolve(0.25, cal)).toBe('MEDIUM');
  });

  it('0.70 → HIGH (borne high incluse)', () => {
    expect(resolver.resolve(0.7, cal)).toBe('HIGH');
  });

  it('0.99 → HIGH', () => {
    expect(resolver.resolve(0.99, cal)).toBe('HIGH');
  });

  it('1.00 → CRITICAL', () => {
    expect(resolver.resolve(1.0, cal)).toBe('CRITICAL');
  });
});