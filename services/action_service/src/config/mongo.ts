/**
 * Client D-02 (MongoDB) — historique des cas de modération et actions.
 * Fournit la connexion paresseuse et les health-checks.
 */

import { MongoClient, type Db } from 'mongodb';

export interface MongoConfig {
  mongodbUri: string;
  mongodbDb: string;
}

export class MongoStore {
  private client: MongoClient | null = null;
  private db: Db | null = null;

  readonly uri: string;
  readonly dbName: string;

  constructor(config: MongoConfig) {
    this.uri = config.mongodbUri;
    this.dbName = config.mongodbDb;
  }

  /** Connecte (paresseux) et retourne la base `dbName`. */
  async connect(): Promise<Db> {
    if (this.client && this.db) return this.db;
    const client = new MongoClient(this.uri, { serverSelectionTimeoutMS: 3000 });
    await client.connect();
    this.client = client;
    this.db = client.db(this.dbName);
    return this.db;
  }

  /** Base déjà connectée, ou erreur explicite si pas encore connectée. */
  dbOrThrow(): Db {
    if (!this.db) throw new Error('Mongo not connected — call connect() first');
    return this.db;
  }

  async ping(): Promise<void> {
    const db = await this.connect();
    await db.command({ ping: 1 });
  }

  async close(): Promise<void> {
    await this.client?.close().catch(() => undefined);
    this.client = null;
    this.db = null;
  }
}