/**
 * MetricsProvider — interface abstraite de collecte de métriques.
 * `record()` bufferise une métrique en mémoire, `flush()` envoie le buffer
 * vers la destination configurée puis le vide.
 */

export interface MetricTag {
  [key: string]: string | number;
}

export interface MetricEntry {
  name: string;
  value: number;
  tags?: MetricTag;
  timestamp: number;
}

export abstract class MetricsProvider {
  protected buffer: MetricEntry[] = [];

  abstract record(name: string, value: number, tags?: MetricTag): void;
  abstract flush(): void;
}