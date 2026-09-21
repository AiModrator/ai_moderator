/**
 * Client D-02 (MongoDB) — historique des cas de modération et actions.
 * Fournit la connexion paresseuse et les health-checks.
 */

import { MongoClient, type Db } from 'mongodb';
import {
  MODERATION_CASES_COLLECTION,
  USER_ACTIONS_COLLECTION,
} from '../types/case.js';

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

  /**
   * Index D-02 (main.md §6) :
   * - `moderation_cases` : unique `moderationCaseId`, `{communityRef, createdAt:-1}`, `{userRef, createdAt:-1}` ;
   * - `user_actions` : `{communityRef, userRef, createdAt:-1}`.
   */
  async ensureIndexes(): Promise<void> {
    const db = await this.connect();

    const cases = db.collection(MODERATION_CASES_COLLECTION);
    await cases.createIndex({ moderationCaseId: 1 }, { unique: true });
    await cases.createIndex({ communityRef: 1, createdAt: -1 });
    await cases.createIndex({ userRef: 1, createdAt: -1 });

    const actions = db.collection(USER_ACTIONS_COLLECTION);
    await actions.createIndex({ communityRef: 1, userRef: 1, createdAt: -1 });
  }

  async close(): Promise<void> {
    await this.client?.close().catch(() => undefined);
    this.client = null;
    this.db = null;
  }
}