/**
 * Types de sévérité de l'Action Service.
 *
 * L'enum Prisma `Severity` (`@ai-moderator/database`) ne porte que
 * `LOW < MEDIUM < HIGH < CRITICAL`. Ce service ajoute `NONE` (score sous
 * `low` → aucune sévérité → aucune action). `NONE` n'est jamais persisté.
 */

import type { Severity as PrismaSeverity } from '@ai-moderator/database';

export type Severity = 'NONE' | PrismaSeverity;

export const SEVERITY_ORDER: readonly Severity[] = Object.freeze([
  'NONE',
  'LOW',
  'MEDIUM',
  'HIGH',
  'CRITICAL',
]);

export function isSeverity(value: string): value is Severity {
  return (SEVERITY_ORDER as readonly string[]).includes(value);
}