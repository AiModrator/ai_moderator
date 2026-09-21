/**
 * Tâche 03 — MetricsProvider (abstrait) + StdoutMetricsProvider.
 * Tests unitaires : buffering + flush vers le sink, cas limites.
 */

import { describe, it, expect } from 'vitest';
import { MetricsProvider } from '../../src/core/metrics/MetricsProvider.js';
import { StdoutMetricsProvider } from '../../src/core/metrics/StdoutMetricsProvider.js';

/** Implémentation abstraite factice pour vérifier l'API de la classe mère. */
class FakeMetricsProvider extends MetricsProvider {
  record(name: string, value: number, tags?: Record<string, string | number>): void {
    this.buffer.push({ name, value, tags, timestamp: Date.now() });
  }
  flush(): void {
    this.buffer = [];
  }
  get pendingCount(): number {
    return this.buffer.length;
  }
}

describe('MetricsProvider (abstrait)', { tags: ['unit'] }, () => {
  it('record() bufferise sans émission immédiate', () => {
    const provider = new FakeMetricsProvider();
    provider.record('my.metric', 1);
    expect(provider.pendingCount).toBe(1);
  });
});

describe('StdoutMetricsProvider', { tags: ['unit'] }, () => {
  it('record() suivi de flush() émet la métrique enregistrée sur le sink', () => {
    const lines: string[] = [];
    const provider = new StdoutMetricsProvider((line) => lines.push(line));

    provider.record('ingestion.request', 42, { communityRef: 'community-1' });
    provider.flush();

    expect(lines).toHaveLength(1);
    const parsed = JSON.parse(lines[0]) as Record<string, unknown>;
    expect(parsed.metric).toBe('ingestion.request');
    expect(parsed.value).toBe(42);
    expect(parsed.tags).toEqual({ communityRef: 'community-1' });
    expect(typeof parsed.timestamp).toBe('string');
  });

  it('flush() sans métrique enregistrée ne produit aucune sortie', () => {
    const lines: string[] = [];
    const provider = new StdoutMetricsProvider((line) => lines.push(line));

    provider.flush();

    expect(lines).toHaveLength(0);
    expect(() => provider.flush()).not.toThrow();
  });

  it('plusieurs record() avant un seul flush() apparaissent tous dans la sortie (batching)', () => {
    const lines: string[] = [];
    const provider = new StdoutMetricsProvider((line) => lines.push(line));

    provider.record('a', 1);
    provider.record('b', 2);
    provider.record('c', 3);
    provider.flush();

    expect(lines).toHaveLength(3);
    const metrics = lines.map((line) => (JSON.parse(line) as { metric: string }).metric);
    expect(metrics).toEqual(['a', 'b', 'c']);
  });

  it('après un flush(), un nouveau flush() sans record() ne réémet pas le buffer (vidé)', () => {
    const lines: string[] = [];
    const provider = new StdoutMetricsProvider((line) => lines.push(line));

    provider.record('x', 1);
    provider.flush();
    provider.flush();

    expect(lines).toHaveLength(1);
    expect(provider.pendingCount).toBe(0);
  });
});