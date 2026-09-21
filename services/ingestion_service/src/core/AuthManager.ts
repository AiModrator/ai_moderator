/**
 * AuthManager — authentifie une requête à partir de sa clé API et résout le
 * contexte `Community` complet nécessaire au reste du pipeline.
 *
 * Lève une `AuthenticationError` si la clé est absente, inconnue ou révoquée.
 * La résolution passe par le cache-aside (`RedisService.getOrSet`) pour éviter
 * une requête base de données à chaque appel.
 */

import type { Community } from '@ai-moderator/database';
import { AuthenticationError } from '../types/errors.js';
import { hashApiKey } from '../utils/hash.js';
import type { Logger } from '../config/logger.js';
import type { ApiKeyRepository } from '../repositories/ApiKeyRepository.js';
import type { RedisService } from './RedisService.js';

const API_KEY_CACHE_PREFIX = 'ing:config:apikey';

export class AuthManager {
  constructor(
    private readonly apiKeyRepository: ApiKeyRepository,
    private readonly redisService: RedisService,
    private readonly apiKeyHmacSecret: string,
    private readonly cacheTtlSeconds: number,
    private readonly logger: Logger
  ) {}

  async authenticate(apiKey: string | undefined): Promise<Community> {
    if (!apiKey || apiKey.length === 0) {
      throw new AuthenticationError('Missing API key');
    }

    const hashedKey = hashApiKey(apiKey, this.apiKeyHmacSecret);
    const cacheKey = `${API_KEY_CACHE_PREFIX}:${hashedKey}`;

    const community = await this.redisService.getOrSet<Community | null>(
      cacheKey,
      () => this.apiKeyRepository.findByHash(hashedKey),
      this.cacheTtlSeconds
    );

    if (!community) {
      this.logger.warn('authentication failed: unknown or revoked API key', {
        hashedKey: hashedKey.slice(0, 8),
      });
      throw new AuthenticationError('Unknown or revoked API key');
    }

    return community;
  }
}