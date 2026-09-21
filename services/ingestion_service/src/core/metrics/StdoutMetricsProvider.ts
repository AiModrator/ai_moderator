/**
 * StdoutMetricsProvider — implémentation de `MetricsProvider` qui émet les
 * métriques bufferisées, formatées une par ligne sur stdout (destination v1).
 */

import { MetricsProvider, MetricEntry, MetricTag } from './MetricsProvider.js';

interface StdoutLine {
  metric: string;
  value: number;
  tags?: MetricTag;
  timestamp: string;
}

export class StdoutMetricsProvider extends MetricsProvider {
  constructor(
    private readonly sink: (line: string) => void = (line) => process.stdout.write(line + '\n')
  ) {
    super();
  }

  record(name: string, value: number, tags?: MetricTag): void {
    this.buffer.push({ name, value, tags, timestamp: Date.now() });
  }

  flush(): void {
    if (this.buffer.length === 0) return;

    const lines = this.buffer.map((entry) => this.format(entry));
    this.buffer = [];
    for (const line of lines) {
      this.sink(line);
    }
  }

  /**
   * Accesseur exposé pour les tests : état du buffer sans déclencher d'envoi.
   */
  get pendingCount(): number {
    return this.buffer.length;
  }

  private format(entry: MetricEntry): string {
    const line: StdoutLine = {
      metric: entry.name,
      value: entry.value,
      tags: entry.tags,
      timestamp: new Date(entry.timestamp).toISOString(),
    };
    return JSON.stringify(line);
  }
}