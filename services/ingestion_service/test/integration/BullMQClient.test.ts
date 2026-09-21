/**
 * Tâche 04 — BullMQClient (producteur BullMQ).
 * Tests d'intégration : Redis/BullMQ réels, queues de test isolées.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { randomUUID } from 'node:crypto';
import { BullMQClient } from '../../src/core/BullMQClient.js';
import { testRedisHost, testRedisPort } from '../utils/redis.js';
import { getWaitingJobs, clearQueue } from '../utils/queue.js';

describe('BullMQClient', { tags: ['integration'] }, () => {
  const queueName = `test-content-${randomUUID()}`;
  const otherQueueName = `test-content-${randomUUID()}`;
  let client: BullMQClient;

  beforeAll(() => {
    client = new BullMQClient(
      { host: testRedisHost(), port: testRedisPort() },
      { defaultAttempts: 2, defaultBackoffMs: 1000 }
    );
  });

  afterAll(async () => {
    await clearQueue(queueName);
    await clearQueue(otherQueueName);
    for (const queue of client.getQueues().values()) {
      await queue.close();
    }
  });

  beforeEach(async () => {
    await clearQueue(queueName);
  });

  it('addJob retourne un Job avec un id', async () => {
    const job = await client.addJob(queueName, { hello: 'world' });
    expect(job.id).toBeDefined();
    expect(typeof job.id).toBe('string');
  });

  it('le job est récupérable avec un payload exact', async () => {
    const payload = { contentId: 'c1', nested: { a: 1 }, list: [1, 2, 3] };
    await client.addJob(queueName, payload);
    const jobs = await getWaitingJobs(queueName);
    expect(jobs).toHaveLength(1);
    expect(jobs[0].data).toEqual(payload);
  });

  it("applique les options par défaut (attempts + backoff exponentiel)", async () => {
    const job = await client.addJob(queueName, { x: 1 });
    expect(job.opts.attempts).toBe(2);
    expect(job.opts.backoff).toEqual({ type: 'exponential', delay: 1000 });
    expect(job.opts.removeOnComplete).toBe(true);
  });

  it('des options explicites écrasent les valeurs par défaut', async () => {
    const job = await client.addJob(queueName, { x: 1 }, { attempts: 5 });
    expect(job.opts.attempts).toBe(5);
  });

  it('réutilise une seule instance de Queue par nom', async () => {
    await client.addJob(otherQueueName, { y: 1 });
    await client.addJob(otherQueueName, { y: 2 });
    expect(client.getQueues().size).toBe(2);
    expect(client.getQueues().has(otherQueueName)).toBe(true);
  });

  it('countJobs compte les jobs en attente', async () => {
    await client.addJob(queueName, { n: 1 });
    await client.addJob(queueName, { n: 2 });
    await client.addJob(queueName, { n: 3 });
    const count = await client.countJobs(queueName, ['waiting', 'delayed']);
    expect(count).toBe(3);
  });
});