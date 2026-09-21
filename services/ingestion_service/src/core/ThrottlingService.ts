/**
 * ThrottlingService — décision métier du throttling : combien de posts d'une
 * communauté peuvent être envoyés maintenant, sans jamais bloquer le service
 * ni dépasser le besoin réel.
 *
 * Délègue l'atomicité à `RedisService.consumeBucket` (bucket global partagé
 * entre toutes les communautés, stocké dans Redis). Si le bucket est vide,
 * attend localement (setTimeout, non bloquant) jusqu'au prochain
 * réapprovisionnement au lieu de retourner `0`.
 */

import type { MetricsProvider } from './metrics/MetricsProvider.js';
import type { Logger } from '../config/logger.js';
import type { RedisService } from './RedisService.js';

export interface ThrottlingConfig {
  capacity: number;
  costPerToken: number;
  refillIntervalMs: number;
}

export class ThrottlingService {
  private readonly bucketKey = 'global';

  constructor(
    private readonly redisService: RedisService,
    private readonly metrics: MetricsProvider,
    private readonly config: ThrottlingConfig,
    private readonly logger: Logger
  ) {}

  /**
   * Réserve jusqu'à `requestedCount` posts. Ne retourne jamais plus que
   * `requestedCount` (borné par le besoin réel). Attends en interne si le
   * bucket est vide, tant qu'il reste des posts à envoyer.
   */
  async reserve(communityRef: string, requestedCount: number): Promise<number> {
    if (requestedCount <= 0) return 0;

    const { costPerToken } = this.config;
    let granted = 0;

    while (granted < requestedCount) {
      const remaining = requestedCount - granted;
      const tokensNeeded = Math.ceil(remaining / costPerToken);

      const tokens = await this.redisService.consumeBucket(this.bucketKey, {
        capacity: this.config.capacity,
        costPerToken,
        refillIntervalMs: this.config.refillIntervalMs,
        requested: tokensNeeded,
      });

      if (tokens > 0) {
        granted += tokens * costPerToken;
      } else {
        await this.waitForNextRefill();
      }
    }

    const awarded = Math.min(granted, requestedCount);
    this.metrics.record('ingestion.throttle.tokens', awarded, { communityRef });
    this.logger.debug('throttle: tokens reserved', { communityRef, awarded });

    return awarded;
  }

  /**
   * Attente locale (non bloquante) jusqu'au prochain réapprovisionnement du
   * bucket. Détermine le temps restant à partir du dernier refill enregistré.
   */
  private async waitForNextRefill(): Promise<void> {
    const state = await this.redisService.getBucketState(this.bucketKey);
    const now = Date.now();
    const lastRefill = state.lastRefill > 0 ? state.lastRefill : now;
    const elapsed = now - lastRefill;
    const waitMs = Math.max(this.config.refillIntervalMs - elapsed, 5);
    await new Promise((resolve) => setTimeout(resolve, waitMs));
  }
}