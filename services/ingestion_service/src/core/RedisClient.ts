/**
 * RedisClient — wrapper bas niveau autour d'ioredis.
 * Seule classe du service autorisée à parler à Redis directement.
 *
 * Contrat :
 *   get(key)                     → Promise<string | null>
 *   set(key, value, ttlSeconds?) → Promise<void>
 *   eval(script, keys, args)     → Promise<any>
 *
 * Réutilise une seule connexion Redis pendant toute la durée du process.
 * Aucune logique métier : opérations Redis pures. Les erreurs de connexion
 * sont propagées comme `RedisError` (typée), jamais un échec silencieux.
 */

import { Redis } from 'ioredis';
import { RedisError } from '../types/errors.js';

export class RedisClient {
  private readonly client: Redis;

  constructor(host: string, port: number, password?: string) {
    this.client = new Redis({
      host,
      port,
      password,
      // Nombre de retries borné : si Redis est injoignable, les commandes
      // rejettent une erreur typée au lieu d'attendre indéfiniment
      // (nécessaire pour la vérification de dépendances au démarrage et pour
      // un échec rapide en cas d'indisponibilité).
      maxRetriesPerRequest: 3,
      retryStrategy(times: number) {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    });

    this.client.on('error', (err: Error) => {
      // Les appels rejettent eux-mêmes une erreur typée ; on ne fait que logguer ici.
      // eslint-disable-next-line no-console
      console.error('[ingestion_service][redis] connection error:', err.message);
    });
  }

  async get(key: string): Promise<string | null> {
    try {
      const value = await this.client.get(key);
      return value === undefined ? null : value;
    } catch (error) {
      throw new RedisError(readErrorMessage(error, 'get'));
    }
  }

  async set(key: string, value: string, ttlSeconds?: number): Promise<void> {
    try {
      if (ttlSeconds !== undefined && ttlSeconds > 0) {
        await this.client.set(key, value, 'EX', ttlSeconds);
      } else {
        await this.client.set(key, value);
      }
    } catch (error) {
      throw new RedisError(readErrorMessage(error, 'set'));
    }
  }

  async eval(script: string, keys: string[], args: string[]): Promise<unknown> {
    try {
      return await this.client.eval(script, keys.length, ...keys, ...args);
    } catch (error) {
      throw new RedisError(readErrorMessage(error, 'eval'));
    }
  }

  /**
   * Vérification de disponibilité au démarrage — retourne `PONG` si la
   * connexion est vivante, rejette sinon (règle : vérifier les dépendances).
   */
  async ping(): Promise<string> {
    try {
      return await this.client.ping();
    } catch (error) {
      throw new RedisError(readErrorMessage(error, 'ping'));
    }
  }

  /**
   * Éteint proprement la connexion (utilisé au shutdown / en fin de tests).
   */
  async disconnect(): Promise<void> {
    try {
      await this.client.quit();
    } catch {
      this.client.disconnect();
    }
  }
}

function readErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message;
  return `unknown ${fallback} error`;
}