/**
 * DataDispatcher — publie un lot de posts déjà autorisé (par ThrottlingService)
 * vers `contentQueue`. Ne contient aucune logique de throttling.
 *
 * Construit **un seul** job `ContentBatchJob` contenant l'ensemble du lot.
 */

import { randomUUID } from 'node:crypto';
import type { Job } from 'bullmq';
import type { RiskClass } from '@ai-moderator/database';
import type { BullMQClient } from './BullMQClient.js';
import type { Logger } from '../config/logger.js';
import type { ContentBatchJob, ContentItem } from '../types/job.js';
import type { IncomingContent } from '../types/payload.js';

const JOB_NAME = 'moderateBatch';

export class DataDispatcher {
  constructor(
    private readonly bullMQClient: BullMQClient,
    private readonly contentQueueName: string,
    private readonly logger: Logger
  ) {}

  async dispatchData(
    posts: IncomingContent[],
    activeRiskClasses: RiskClass[],
    communityRef: string
  ): Promise<Job> {
    if (posts.length === 0) {
      throw new Error('dispatchData: cannot dispatch an empty batch');
    }

    const payload: ContentBatchJob = {
      batchId: randomUUID(),
      communityRef,
      activeClasses: activeRiskClasses,
      items: posts.map(toContentItem),
      retryState: null,
    };

    const job = await this.bullMQClient.addJob(
      this.contentQueueName,
      payload,
      undefined,
      JOB_NAME
    );

    this.logger.info('batch dispatched', {
      batchId: payload.batchId,
      communityRef,
      itemCount: payload.items.length,
      jobId: job.id,
    });

    return job;
  }
}

function toContentItem(post: IncomingContent): ContentItem {
  return {
    contentId: post.contentId,
    contentType: post.contentType,
    userRef: post.userRef,
    timestamp: post.timestamp,
    text: post.data.text ?? null,
    attachments: (post.data.attachments ?? []).map((attachment) => ({
      type: attachment.type,
      url: attachment.url,
    })),
  };
}