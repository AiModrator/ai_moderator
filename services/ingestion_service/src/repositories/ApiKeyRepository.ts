/**
 * ApiKeyRepository — résout une clé API (déjà hashée) vers la `Community`
 * à laquelle elle appartient (relation `ApiKey.communityId → Community`).
 */

import type { Community } from '@ai-moderator/database';
import databaseService from '../core/DatabaseService.js';

export class ApiKeyRepository {
  /**
   * Retourne la `Community` rattachée à la clé non révoquée, ou `null`
   * (jamais une exception) si la clé n'existe pas ou est révoquée.
   */
  async findByHash(hashedKey: string): Promise<Community | null> {
    const apiKey = await databaseService.client.apiKey.findFirst({
      where: {
        hashedKey,
        revokedAt: null,
      },
      include: {
        community: true,
      },
    });

    return apiKey ? apiKey.community : null;
  }
}