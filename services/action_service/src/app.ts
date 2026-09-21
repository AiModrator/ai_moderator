/**
 * Fabrique de l'application Express de l'Action Service.
 * Les routes sont injectées (routers) — l'app n'a aucune connaissance métier.
 */

import express, { type Router } from 'express';

export interface AppOptions {
  routers: Router[];
}

export function createApp(options: AppOptions): express.Express {
  const app = express();
  app.use(express.json());

  for (const router of options.routers) {
    app.use(router);
  }

  app.use((_req, res) => {
    res.status(404).json({ error: 'not_found' });
  });

  return app;
}