/**
 * IngestionController — orchestre le cycle de vie d'une requête webhook.
 *
 * Flux (cf. `.agent/phase-02/main.md` §5) :
 *   1. valide le payload ;
 *   2. authentifie et résout la communauté ;
 *   3. récupère les classes de risque actives (cache-aside via RedisService) ;
 *   4. répond 202 immédiatement (avant tout throttling) ;
 *   5. lance en arrière-plan la boucle throttlée de dispatch.
 *
 * Un plafond de backlog par communauté (décision 2, §6) borne le nombre de
 * posts en attente : au-delà, la requête est rejetée en HTTP 429.
 */

import { randomUUID } from 'node:crypto';
import type { Community, RiskClass } from '@ai-moderator/database';
import type { Logger } from '../config/logger.js';
import type { AuthManager } from '../core/AuthManager.js';
import type { DataDispatcher } from '../core/DataDispatcher.js';
import type { RedisService } from '../core/RedisService.js';
import type { ThrottlingService } from '../core/ThrottlingService.js';
import type { Validator } from '../core/Validator.js';
import type { WorkflowRepository } from '../repositories/WorkflowRepository.js';
import {
  AuthenticationError,
  ValidationError,
} from '../types/errors.js';
import type { IncomingContent, WebhookPayload } from '../types/payload.js';

const WORKFLOW_CACHE_PREFIX = 'ing:config:workflow';

export interface WebhookRequest {
  apiKey?: string;
  body: unknown;
}

export interface WebhookResponse {
  status: number;
  body: Record<string, unknown>;
}

export interface IngestionControllerDeps {
  validator: Validator;
  authManager: AuthManager;
  workflowRepository: WorkflowRepository;
  throttlingService: ThrottlingService;
  dataDispatcher: DataDispatcher;
  redisService: RedisService;
  logger: Logger;
  cacheConfigTtlSeconds: number;
  backlogMaxPostsPerCommunity: number;
  backlogTtlSeconds: number;
}

export class IngestionController {
  private readonly deps: IngestionControllerDeps;

  constructor(deps: IngestionControllerDeps) {
    this.deps = deps;
  }

  async handleWebhook(request: WebhookRequest): Promise<WebhookResponse> {
    let payload: WebhookPayload;
    try {
      payload = this.deps.validator.validate(request.body);
    } catch (error) {
      if (error instanceof ValidationError) {
        return { status: 400, body: { error: 'validation_failed', message: error.message, fields: error.fields } };
      }
      throw error;
    }

    let community: Community;
    try {
      community = await this.deps.authManager.authenticate(request.apiKey);
    } catch (error) {
      if (error instanceof AuthenticationError) {
        return { status: 401, body: { error: 'authentication_failed', message: error.message } };
      }
      throw error;
    }

    const activeClasses = await this.deps.redisService.getOrSet(
      `${WORKFLOW_CACHE_PREFIX}:${community.id}`,
      () => this.deps.workflowRepository.getActiveRiskClasses(community.id),
      this.deps.cacheConfigTtlSeconds
    );

    const communityRef = community.id;
    const totalItems = payload.items.length;

    // Plafond de backlog par communauté (décision 2) — rejet HTTP avant toute
    // acceptation, pour borner le remplissage de la queue.
    const currentBacklog = await this.deps.redisService.getBacklog(communityRef);
    if (currentBacklog + totalItems > this.deps.backlogMaxPostsPerCommunity) {
      return {
        status: 429,
        body: {
          error: 'backlog_exceeded',
          message: `Backlog limit exceeded for this community (max ${this.deps.backlogMaxPostsPerCommunity} posts)`,
        },
      };
    }
    await this.deps.redisService.changeBacklog(
      communityRef,
      totalItems,
      this.deps.backlogTtlSeconds
    );

    const acceptedId = randomUUID();

    // Traitement throttlé en arrière-plan, détaché du cycle requête/réponse.
    void this.processBatch(communityRef, payload.items, activeClasses).catch((error) => {
      this.deps.logger.error('background dispatch failed', { communityRef, err: error });
    });

    return {
      status: 202,
      body: { status: 'accepted', acceptedId, itemCount: totalItems, communityRef },
    };
  }

  /**
   * Boucle throttlée : tant qu'il reste des posts, réserve des tokens, découpe
   * le lot correspondant et le transmet au `DataDispatcher`. Décrémente le
   * backlog au fil des dispatches effectués.
   */
  private async processBatch(
    communityRef: string,
    items: IncomingContent[],
    activeClasses: RiskClass[]
  ): Promise<void> {
    let remaining = items;
    let dispatched = 0;

    try {
      while (remaining.length > 0) {
        const authorized = await this.deps.throttlingService.reserve(communityRef, remaining.length);
        const lot = remaining.slice(0, authorized);
        await this.deps.dataDispatcher.dispatchData(lot, activeClasses, communityRef);
        await this.deps.redisService.changeBacklog(communityRef, -lot.length, this.deps.backlogTtlSeconds);
        dispatched += lot.length;
        remaining = remaining.slice(lot.length);
      }
    } catch (error) {
      // En cas d'échec, on rend le reste du backlog non dispatché.
      await this.deps.redisService
        .changeBacklog(communityRef, -remaining.length, this.deps.backlogTtlSeconds)
        .catch(() => undefined);
      throw error;
    }

    this.deps.logger.info('batch processing completed', { communityRef, dispatched });
  }
}