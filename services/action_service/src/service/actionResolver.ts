/**
 * ActionResolver — logique pure : mapping `(classe, sévérité) → actions`
 * via les règles du workflow (D-04). Une règle = un couple exact
 * `(riskClass, severity)` → 0..n `contentActions` + 0..n `userActions`.
 *
 * Règle absente pour le couple → `{ contentActions: [], userActions: [] }`
 * (jamais d'erreur, log warning en amont). Actions dédoublonnées.
 */

import type { RiskClass, Rule } from '@ai-moderator/database';
import type { ActionsResult } from '../types/actions.js';
import { EMPTY_ACTIONS } from '../types/actions.js';
import type { Severity } from '../types/severity.js';

export class ActionResolver {
  resolve(riskClass: RiskClass, severity: Severity, rules: Rule[]): ActionsResult {
    if (severity === 'NONE') return EMPTY_ACTIONS;

    const rule = rules.find((r) => r.riskClass === riskClass && r.severity === severity);

    if (!rule) return EMPTY_ACTIONS;

    const contentActions = [...new Set(rule.contentActions)];
    const userActions = [...new Set(rule.userActions)];

    return { contentActions, userActions };
  }
}