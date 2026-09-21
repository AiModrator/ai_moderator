/**
 * WorkflowRepository — récupère les classes de risque actives d'une
 * communauté à partir de son `Workflow` et de ses `Rule`.
 *
 * Retourne la liste **dédupliquée** des `riskClass` présentes dans au moins
 * une règle du workflow. Aucune connaissance de Redis (cache-aside géré en
 * amont par `AuthManager` / `IngestionController`).
 */

import type { RiskClass } from '@ai-moderator/database';
import databaseService from '../core/DatabaseService.js';

export class WorkflowRepository {
  /**
   * Classes de risque actives, dédupliquées. Tableau vide si la communauté
   * n'a pas de workflow ou que celui-ci n'a aucune règle.
   */
  async getActiveRiskClasses(communityId: string): Promise<RiskClass[]> {
    const workflow = await databaseService.client.workflow.findUnique({
      where: { communityId },
      include: { rules: true },
    });

    if (!workflow) return [];

    const seen = new Set<RiskClass>();
    for (const rule of workflow.rules) {
      seen.add(rule.riskClass);
    }

    return [...seen];
  }
}