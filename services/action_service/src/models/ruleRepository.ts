/**
 * RuleRepository — règles du workflow (D-04).
 * Une règle = un couple `(riskClass, severity)` → 0..n actions contenu/utilisateur.
 */

import type { Rule } from '@ai-moderator/database';
import { ConfigReadError } from '../exceptions/index.js';
import { prismaClient } from '../config/prisma.js';
import type { Logger } from '../utils/logger.js';

export class RuleRepository {
  constructor(private readonly logger: Logger) {}

  async findByWorkflow(workflowId: string): Promise<Rule[]> {
    try {
      return await prismaClient.rule.findMany({ where: { workflowId } });
    } catch (error) {
      this.logger.error('D-04 read failed (rules)', { workflowId, err: error });
      throw new ConfigReadError(`failed to read rules for workflow ${workflowId}`);
    }
  }
}