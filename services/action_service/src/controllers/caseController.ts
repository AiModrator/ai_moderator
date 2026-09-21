/**
 * API Lecture — `GET /cases/:id` (filet de sécurité spec §7.2).
 * Retourne le cas D-02 complet ou 404. Sérialise les dates en ISO et
 * masque `_id` (identifiant interne Mongo).
 */

import { Router } from 'express';
import type { ModerationCaseRepository } from '../models/moderationCaseRepository.js';
import type { ModerationCase } from '../types/case.js';
import type { Logger } from '../utils/logger.js';

export class CaseController {
  constructor(
    private readonly caseRepository: ModerationCaseRepository,
    private readonly logger: Logger
  ) {}

  public router(): Router {
    const router = Router();

    router.get('/cases/:id', async (req, res) => {
      const { id } = req.params;
      try {
        const cse = await this.caseRepository.findById(id);
        if (!cse) {
          res.status(404).json({ error: 'case_not_found', moderationCaseId: id });
          return;
        }
        res.json(serializeCase(cse));
      } catch (error) {
        this.logger.error('GET /cases/:id failed', { id, err: error });
        res.status(500).json({ error: 'internal_error' });
      }
    });

    return router;
  }
}

/** Sérialisation API : `_id` retiré, dates en ISO 8601 (UTC). */
export function serializeCase(cse: ModerationCase): Record<string, unknown> {
  const { _id: _internal, ...rest } = (cse as ModerationCase & { _id?: unknown });
  return {
    ...rest,
    contentTimestamp: cse.contentTimestamp.toISOString(),
    createdAt: cse.createdAt.toISOString(),
    updatedAt: cse.updatedAt.toISOString(),
    callback: {
      ...cse.callback,
      deliveredAt: cse.callback.deliveredAt ? cse.callback.deliveredAt.toISOString() : null,
    },
  };
}