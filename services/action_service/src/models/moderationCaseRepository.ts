/**
 * ModerationCaseRepository — historique D-02, collection `moderation_cases`.
 * Upsert idempotent par `moderationCaseId` (déterministe, re-jeu sans doublon),
 * lecture par id et mise à jour du statut de livraison du callback.
 */

import type { CallbackInfo, ModerationCase } from '../types/case.js';
import { MODERATION_CASES_COLLECTION } from '../types/case.js';
import { HistoryWriteError } from '../exceptions/index.js';
import type { MongoStore } from '../config/mongo.js';
import type { Logger } from '../utils/logger.js';

export class ModerationCaseRepository {
  constructor(
    private readonly store: MongoStore,
    private readonly logger: Logger
  ) {}

  async upsert(cse: ModerationCase): Promise<void> {
    const collection = this.store.dbOrThrow().collection<ModerationCase>(MODERATION_CASES_COLLECTION);
    try {
      await collection.replaceOne({ moderationCaseId: cse.moderationCaseId }, cse, { upsert: true });
    } catch (error) {
      this.logger.error('D-02 write failed (upsert case)', { moderationCaseId: cse.moderationCaseId, err: error });
      throw new HistoryWriteError(`failed to upsert case ${cse.moderationCaseId}`);
    }
  }

  async findById(moderationCaseId: string): Promise<ModerationCase | null> {
    try {
      const collection = this.store.dbOrThrow().collection<ModerationCase>(MODERATION_CASES_COLLECTION);
      return await collection.findOne({ moderationCaseId });
    } catch (error) {
      this.logger.error('D-02 read failed (case)', { moderationCaseId, err: error });
      throw new HistoryWriteError(`failed to read case ${moderationCaseId}`);
    }
  }

  async updateCallback(moderationCaseId: string, callback: CallbackInfo): Promise<void> {
    try {
      const collection = this.store.dbOrThrow().collection<ModerationCase>(MODERATION_CASES_COLLECTION);
      await collection.updateOne({ moderationCaseId }, { $set: { callback } });
    } catch (error) {
      this.logger.error('D-02 write failed (callback status)', { moderationCaseId, err: error });
      throw new HistoryWriteError(`failed to update callback status for case ${moderationCaseId}`);
    }
  }
}