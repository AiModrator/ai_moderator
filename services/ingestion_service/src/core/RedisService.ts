/**
 * RedisService — couche cache-aside unique devant Redis.
 * Sert à la fois le cache de configuration communauté (clé API, classes actives)
 * et l'état atomique du bucket de tokens global.
 *
 * Contrat :
 *   getOrSet<T>(key, fallbackFn, ttlSeconds) → Promise<T>
 *   consumeBucket(key, { capacity, costPerToken, refillIntervalMs, requested }) → Promise<number>
 *   resetBucket(key, params)                  → Promise<void>   (utile en test)
 */

import { RedisClient } from './RedisClient.js';

export interface BucketParams {
  capacity: number;
  costPerToken: number;
  refillIntervalMs: number;
  requested: number;
}

interface BucketState {
  tokens: number;
  lastRefill: number;
}

const BUCKET_KEY_PREFIX = 'ing:throttle';

const BACKLOG_KEY_PREFIX = 'ing:backlog';

/**
 * Incrément atomique (positif ou négatif) d'un compteur de backlog, avec TTL.
 * Le TTL sert d'auto-guérison : si un process crashe avant de décrémenter, le
 * compteur retombe à 0 au bout du TTL (direction sûre : on rejette moins,
 * jamais on ne laisse déborder).
 */
const BACKLOG_INCR_SCRIPT = `
local value = redis.call('INCRBY', KEYS[1], ARGV[1])
local ttl = tonumber(ARGV[2])
if ttl > 0 then
  redis.call('EXPIRE', KEYS[1], ttl)
end
if value < 0 then
  redis.call('SET', KEYS[1], '0')
  value = 0
end
return value
`;

/**
 * Lazy refill + consommation atomiques.
 *
 * Un bucket neuf part avec `capacity` tokens, horodatés à `now`. À chaque
 * consommation on accrédite les unités dues (intervalles entiers écoulés
 * depuis le dernier refill), plafonnées à la capacité, puis on retire jusqu'à
 * `requested` tokens. Le tout en une seule opération Lua : deux instances
 * concurrentes ne peuvent jamais consommer plus que la capacité totale.
 */
const BUCKET_SCRIPT = `
local tokensKey = KEYS[1]
local tsKey = KEYS[2]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refillIntervalMs = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local tokens = tonumber(redis.call('GET', tokensKey) or tostring(capacity))
local lastRefill = tonumber(redis.call('GET', tsKey) or '0')

if lastRefill == 0 then
  tokens = capacity
  lastRefill = now
else
  local elapsedUnits = math.floor((now - lastRefill) / refillIntervalMs)
  if elapsedUnits > 0 then
    tokens = math.min(capacity, tokens + elapsedUnits)
    lastRefill = lastRefill + elapsedUnits * refillIntervalMs
  end
end

local granted = math.min(requested, tokens)
tokens = tokens - granted

redis.call('SET', tokensKey, tostring(tokens))
redis.call('SET', tsKey, tostring(lastRefill))
return tostring(granted)
`;

export class RedisService {
  constructor(private readonly redisClient: RedisClient) {}

  /**
   * Cache-aside générique : cache hit → retourne la valeur sans appeler
   * `fallbackFn`. Cache miss → appelle `fallbackFn`, stocke avec le `ttl`.
   */
  async getOrSet<T>(key: string, fallbackFn: () => Promise<T>, ttlSeconds: number): Promise<T> {
    const cached = await this.redisClient.get(key);
    if (cached !== null) {
      return JSON.parse(cached) as T;
    }

    const value = await fallbackFn();
    await this.redisClient.set(key, JSON.stringify(value), ttlSeconds);
    return value;
  }

  /**
   * Consomme jusqu'à `requested` tokens (jamais plus) en une opération
   * atomique Lua : lazy refill calculé au moment de l'appel + consommation.
   * Retourne le nombre de tokens effectivement accordés.
   */
  async consumeBucket(key: string, params: BucketParams): Promise<number> {
    if (params.requested <= 0) return 0;

    const tokensKey = `${BUCKET_KEY_PREFIX}:tokens:${key}`;
    const tsKey = `${BUCKET_KEY_PREFIX}:ts:${key}`;
    const now = Date.now();

    const result = await this.redisClient.eval(BUCKET_SCRIPT, [tokensKey, tsKey], [
      String(now),
      String(params.capacity),
      String(params.refillIntervalMs),
      String(params.requested),
    ]);

    return Number(result);
  }

  /**
   * Réinitialise l'état du bucket (utile pour les tests et la mise à zéro).
   */
  async resetBucket(key: string, params: Partial<BucketParams> = {}): Promise<void> {
    const tokensKey = `${BUCKET_KEY_PREFIX}:tokens:${key}`;
    const tsKey = `${BUCKET_KEY_PREFIX}:ts:${key}`;
    await this.redisClient.set(tokensKey, String(params.capacity ?? 0));
    await this.redisClient.set(tsKey, String(Date.now()));
  }

  /**
   * État courant d'un bucket (inspection/tests).
   */
  async getBucketState(key: string): Promise<BucketState> {
    const tokensKey = `${BUCKET_KEY_PREFIX}:tokens:${key}`;
    const tsKey = `${BUCKET_KEY_PREFIX}:ts:${key}`;
    const tokens = await this.redisClient.get(tokensKey);
    const lastRefill = await this.redisClient.get(tsKey);
    return {
      tokens: tokens === null ? 0 : Number(tokens),
      lastRefill: lastRefill === null ? 0 : Number(lastRefill),
    };
  }

  /**
   * Nombre actuel de posts en attente de traitement pour une communauté.
   */
  async getBacklog(communityRef: string): Promise<number> {
    const value = await this.redisClient.get(`${BACKLOG_KEY_PREFIX}:${communityRef}`);
    return value === null ? 0 : Math.max(0, Number(value));
  }

  /**
   * Incrémente (`delta` positif) ou décrémente (`delta` négatif) le backlog
   * d'une communauté, atomiquement. Retourne la nouvelle valeur (bornée à 0).
   */
  async changeBacklog(communityRef: string, delta: number, ttlSeconds: number): Promise<number> {
    const value = await this.redisClient.eval(BACKLOG_INCR_SCRIPT, [`${BACKLOG_KEY_PREFIX}:${communityRef}`], [
      String(delta),
      String(ttlSeconds),
    ]);
    return Math.max(0, Number(value));
  }

  async resetBacklog(communityRef: string): Promise<void> {
    await this.redisClient.set(`${BACKLOG_KEY_PREFIX}:${communityRef}`, '0');
  }

  async disconnect(): Promise<void> {
    await this.redisClient.disconnect();
  }
}