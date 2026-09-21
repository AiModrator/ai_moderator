/**
 * CommunityRepository — résout `communityRef` (canonique = `Community.id`,
 * résolu par l'Ingestion Service lors de l'authentification) vers le
 * contexte de décision D-04 : communauté + workflow + callbackUrl + accountId.
 */

import type { CommunityContext } from '../types/community.js';
import { ConfigReadError, CommunityNotFoundError } from '../exceptions/index.js';
import { prismaClient } from '../config/prisma.js';
import type { Logger } from '../utils/logger.js';

export class CommunityRepository {
  constructor(private readonly logger: Logger) {}

  async findByRef(communityRef: string): Promise<CommunityContext> {
    try {
      const community = await prismaClient.community.findUnique({
        where: { id: communityRef },
        include: { workflow: true },
      });

      if (!community) {
        throw new CommunityNotFoundError(`community not found: ${communityRef}`);
      }

      return {
        communityId: community.id,
        accountId: community.accountId,
        callbackUrl: community.callbackUrl,
        workflowId: community.workflow?.id ?? null,
      };
    } catch (error) {
      if (error instanceof CommunityNotFoundError) throw error;
      this.logger.error('D-04 read failed (community)', { communityRef, err: error });
      throw new ConfigReadError(`failed to read community ${communityRef}`);
    }
  }
}