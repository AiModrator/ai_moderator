/**
 * UserActionRepository — journal des sanctions utilisateur, D-02,
 * collection `user_actions`. Insertion multiple.
 */

import type { UserActionRecord } from '../types/case.js';
import { USER_ACTIONS_COLLECTION } from '../types/case.js';
import { HistoryWriteError } from '../exceptions/index.js';
import type { MongoStore } from '../config/mongo.js';
import type { Logger } from '../utils/logger.js';

export class UserActionRepository {
  constructor(
    private readonly store: MongoStore,
    private readonly logger: Logger
  ) {}

  async insertMany(records: UserActionRecord[]): Promise<void> {
    if (records.length === 0) return;
    try {
      const collection = this.store.dbOrThrow().collection<UserActionRecord>(USER_ACTIONS_COLLECTION);
      await collection.insertMany(records);
    } catch (error) {
      this.logger.error('D-02 write failed (user actions)', { count: records.length, err: error });
      throw new HistoryWriteError(`failed to insert user actions (${records.length})`);
    }
  }
}