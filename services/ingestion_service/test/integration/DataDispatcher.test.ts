/**
 * Tâche 11 — DataDispatcher (publication d'un lot vers contentQueue).
 * Tests d'intégration : Redis/BullMQ réels.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { randomUUID } from 'node:crypto';
import { RiskClass } from '@ai-moderator/database';
import { BullMQClient } from '../../src/core/BullMQClient.js';
import { DataDispatcher } from '../../src/core/DataDispatcher.js';
import { Logger } from '../../src/config/logger.js';
import type { ContentBatchJob } from '../../src/types/job.js';
import { testRedisHost, testRedisPort } from '../utils/redis.js';
import { waitForJobs, clearQueue } from '../utils/queue.js';
import { makeItem } from '../utils/payload.js';

describe('DataDispatcher', { tags: ['integration'] }, () => {
  const queueName = `test-dispatch-${randomUUID()}`;
  let client: BullMQClient;
  let dispatcher: DataDispatcher;

  beforeAll(() => {
    client = new BullMQClient({ host: testRedisHost(), port: testRedisPort() });
    dispatcher = new DataDispatcher(client, queueName, new Logger('error'));
  });

  afterAll(async () => {
    await clearQueue(queueName);
    for (const queue of client.getQueues().values()) {
      await queue.close();
    }
  });

  beforeEach(async () => {
    await clearQueue(queueName);
  });

  it('N posts → exactement un job contenant N items', async () => {
    const posts = [makeItem({ contentId: 'a' }), makeItem({ contentId: 'b' }), makeItem({ contentId: 'c' })];
    const communityRef = 'community-1';
    const activeClasses = [RiskClass.SPAM, RiskClass.TOXICITY];

    await dispatcher.dispatchData(posts, activeClasses, communityRef);
    const jobs = await waitForJobs(queueName, 1);

    expect(jobs).toHaveLength(1);
    const payload = jobs[0].data as ContentBatchJob;
    expect(payload.items).toHaveLength(3);
    expect(payload.communityRef).toBe(communityRef);
    expect(payload.activeClasses).toEqual(activeClasses);
    expect(payload.retryState).toBeNull();
    expect(typeof payload.batchId).toBe('string');
  });

  it('le nom du job est moderateBatch', async () => {
    await dispatcher.dispatchData([makeItem()], [], 'community-1');
    const jobs = await waitForJobs(queueName, 1);
    expect(jobs[0].name).toBe('moderateBatch');
  });

  it('le job normalise text/attachments au contrat ContentItem', async () => {
    const posts = [makeItem({ contentId: 'd', text: null, attachments: [] })];
    await dispatcher.dispatchData(posts, [], 'community-2');
    const jobs = await waitForJobs(queueName, 1);
    const payload = jobs[0].data as ContentBatchJob;

    expect(payload.items[0]).toMatchObject({
      contentId: 'd',
      text: null,
      attachments: [],
    });
  });

  it('lot vide → erreur (aucun job publié)', async () => {
    await expect(dispatcher.dispatchData([], [], 'community-1')).rejects.toThrow();
    await new Promise((resolve) => setTimeout(resolve, 150));
    await expect(waitForJobs(queueName, 1, 300)).rejects.toThrow();
  });
});