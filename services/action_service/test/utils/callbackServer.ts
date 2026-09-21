/**
 * Serveur HTTP de test pour le CallbackClient : file de réponses,
 * comptage de requêtes, corps capturé, réponse bloquante (timeout) simulée.
 */

import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';

export type CannedResponse = {
  status: number;
  /** Par défaut envoie `{}`. */
  body?: string;
  /** Ne répond jamais (provoque le timeout côté client). */
  hang?: boolean;
  /** Délai avant réponse (ms). */
  delayMs?: number;
};

export class TestCallbackServer {
  readonly server: Server;
callCount = 0;
  lastBody: unknown = null;
  lastHeaders: Record<string, string | undefined> = {};

  private responses: CannedResponse[] = [];

  constructor() {
    this.server = createServer((req: IncomingMessage, res: ServerResponse) => {
      this.callCount += 1;

      let body = '';
      req.on('data', (chunk: Buffer) => {
        body += chunk.toString('utf8');
      });
      req.on('end', () => {
        this.lastBody = body === '' ? null : JSON.parse(body);
        for (const header of Object.keys(req.headers)) {
          this.lastHeaders[header] = req.headers[header] as string | undefined;
        }

        const canned = this.responses.shift() ?? { status: 200 };
        if (canned.hang === true) return;

        const reply = () => {
          res.writeHead(canned.status, { 'Content-Type': 'application/json' });
          res.end(canned.body ?? '{}');
        };
        if (canned.delayMs) {
          setTimeout(reply, canned.delayMs);
        } else {
          reply();
        }
      });
    });
    this.responses = [];
  }

  /** File d'attente des réponses, dans l'ordre (épuisée → 200). */
  queue(responses: CannedResponse[]): void {
    this.responses.push(...responses);
  }

  listen(): Promise<number> {
    return new Promise((resolve) => {
      this.server.listen(0, '127.0.0.1', () => {
        const address = this.server.address();
        resolve(typeof address === 'object' && address !== null ? address.port : 0);
      });
    });
  }

  close(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server.close((err) => (err ? reject(err) : resolve()));
    });
  }
}