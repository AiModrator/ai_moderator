/**
 * Backoff exponentiel plafonné : `delayFor(attempt) = min(base * 2^(attempt-1), max)`.
 * `attempt` commence à 1 (premier délai après le 1er échec = `base`).
 */

export function delayFor(attempt: number, baseDelayMs: number, maxDelayMs: number): number {
  const exponential = baseDelayMs * Math.pow(2, attempt - 1);
  return Math.min(exponential, maxDelayMs);
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function delaySequence(baseDelayMs: number, maxDelayMs: number, maxAttempts: number): number[] {
  return Array.from({ length: maxAttempts }, (_, i) => delayFor(i + 1, baseDelayMs, maxDelayMs));
}