/**
 * Hashage HMAC des clés API brutes avant stockage/recherche.
 * Le secret est fourni par l'appelant (`Settings.apiKeyHmacSecret`), jamais
 * codé en dur, pour éviter toute fuite.
 */

import { createHmac } from 'node:crypto';

export function hashApiKey(apiKey: string, secret: string): string {
  return createHmac('sha256', secret).update(apiKey).digest('hex');
}