/**
 * Couche HTTP Express de l'Ingestion Service.
 * Mappe les requêtes vers `IngestionController.handleWebhook` et expose
 * un endpoint de healthcheck pour vérifier les dépendances.
 */

import express, { type Express, type NextFunction, type Request, type Response } from 'express';
import type { Logger } from './logger.js';
import type { IngestionController } from '../controllers/IngestionController.js';
import { ApiError } from '../types/errors.js';

export interface ExpressAppDeps {
  controller: IngestionController;
  logger: Logger;
}

export function createApp(deps: ExpressAppDeps): Express {
  const app = express();
  app.use(express.json({ limit: '2mb' }));

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/webhook', async (req: Request, res: Response, next: NextFunction) => {
    try {
      const apiKey = extractBearerToken(req.headers['authorization']);
      const response = await deps.controller.handleWebhook({ apiKey, body: req.body });
      res.status(response.status).json(response.body);
    } catch (error) {
      next(error);
    }
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ApiError) {
      res.status(err.statusCode).json({ error: err.name, message: err.message });
      return;
    }
    deps.logger.error('unhandled request error', { err });
    res.status(500).json({ error: 'internal_error' });
  });

  return app;
}

function extractBearerToken(header: string | undefined): string | undefined {
  if (!header) return undefined;
  const match = /^Bearer\s+(.+)$/i.exec(header.trim());
  return match ? match[1] : undefined;
}