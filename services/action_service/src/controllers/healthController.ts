/**
 * Endpoint de disponibilité — `GET /health`.
 * 200 si Prisma (D-04) + Mongo (D-02) + Redis sont joignables, sinon 503.
 */

import { Router } from 'express';
import type { Logger } from '../utils/logger.js';

export interface DependencyChecks {
  checkPrisma: () => Promise<void>;
  checkMongo: () => Promise<void>;
  checkRedis: () => Promise<void>;
}

export class HealthController {
  constructor(
    private readonly deps: DependencyChecks,
    private readonly logger: Logger
  ) {}

  public router(): Router {
    const router = Router();

    router.get('/health', async (_req, res) => {
      const dependencies: Record<string, boolean> = {};
      let healthy = true;

      const checks: Array<[string, () => Promise<void>]> = [
        ['postgres', this.deps.checkPrisma],
        ['mongo', this.deps.checkMongo],
        ['redis', this.deps.checkRedis],
      ];

      for (const [name, check] of checks) {
        try {
          await check();
          dependencies[name] = true;
        } catch (error) {
          dependencies[name] = false;
          healthy = false;
          this.logger.error('health check failed', { dependency: name, err: error });
        }
      }

      res.status(healthy ? 200 : 503).json({
        status: healthy ? 'ok' : 'degraded',
        dependencies,
      });
    });

    return router;
  }
}