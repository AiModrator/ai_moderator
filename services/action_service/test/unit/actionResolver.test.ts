/**
 * Tâche 03 — ActionResolver (mapping (classe, sévérité) → actions, logique pure).
 */

import { describe, it, expect } from 'vitest';
import type { Rule } from '@ai-moderator/database';
import { ActionResolver } from '../../src/service/actionResolver.js';

const resolver = new ActionResolver();

function makeRule(partial: Partial<Rule>): Rule {
  return {
    id: 'rule-1',
    workflowId: 'wf-1',
    riskClass: 'TOXICITY',
    severity: 'HIGH',
    contentActions: ['DELETE_POST'],
    userActions: ['TIMEOUT_USER'],
    ...partial,
  };
}

describe('ActionResolver', { tags: ['unit'] }, () => {
  it('règle exacte (TOXICITY, HIGH) → DELETE_POST + TIMEOUT_USER', () => {
    const result = resolver.resolve('TOXICITY', 'HIGH', [makeRule({})]);
    expect(result).toEqual({ contentActions: ['DELETE_POST'], userActions: ['TIMEOUT_USER'] });
  });

  it('sévérité NONE → aucune action, même si une règle existe', () => {
    const result = resolver.resolve('TOXICITY', 'NONE', [makeRule({})]);
    expect(result).toEqual({ contentActions: [], userActions: [] });
  });

  it('règle absente pour le couple (classe, sévérité) → listes vides, pas d’erreur', () => {
    const rules = [makeRule({ riskClass: 'TOXICITY', severity: 'HIGH' })];
    expect(resolver.resolve('TOXICITY', 'LOW', rules)).toEqual({ contentActions: [], userActions: [] });
    expect(resolver.resolve('SEXUAL', 'HIGH', rules)).toEqual({ contentActions: [], userActions: [] });
  });

  it('dédoublonne les actions identiques', () => {
    const rules = [
      makeRule({ contentActions: ['DELETE_POST', 'DELETE_POST'], userActions: ['BAN_USER', 'BAN_USER'] }),
    ];
    const result = resolver.resolve('TOXICITY', 'HIGH', rules);
    expect(result.contentActions).toEqual(['DELETE_POST']);
    expect(result.userActions).toEqual(['BAN_USER']);
  });

  it('sélectionne la règle exacte parmi plusieurs (pas de fusion entre sévérités)', () => {
    const rules = [
      makeRule({ severity: 'MEDIUM', contentActions: ['HIDE_POST'], userActions: ['WARN_USER'] }),
      makeRule({ severity: 'HIGH', contentActions: ['DELETE_POST'], userActions: ['BAN_USER'] }),
    ];
    const result = resolver.resolve('TOXICITY', 'MEDIUM', rules);
    expect(result).toEqual({ contentActions: ['HIDE_POST'], userActions: ['WARN_USER'] });
  });

  it('cas des enums (valeurs Prisma)', () => {
    const rules = [
      makeRule({ riskClass: 'SEXUAL', severity: 'CRITICAL', contentActions: ['DELETE_POST'], userActions: ['BAN_USER'] }),
    ];
    expect(resolver.resolve('SEXUAL', 'CRITICAL', rules)).toEqual({
      contentActions: ['DELETE_POST'],
      userActions: ['BAN_USER'],
    });
  });
});