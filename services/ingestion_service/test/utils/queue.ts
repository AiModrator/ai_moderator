/**
 * Utilitaires d'inspection de la queue BullMQ pour les tests.
 */

import { Queue, type Job, type JobsOptions } from 'bullmq';
import { testRedisHost, testRedisPort } from './redis.js';

export function makeQueue(queueName: string): Queue {
  return new Queue(queueName, {
    connection: { host: testRedisHost(), port: testRedisPort() },
  });
}

export async function getWaitingJobs(queueName: string): Promise<Job[]> {
  const queue = makeQueue(queueName);
  try {
    const jobs = await queue.getJobs(['waiting', 'delayed', 'active', 'completed', 'failed'], 0, -1);
    return jobs;
  } finally {
    await queue.close();
  }
}

export async function getWaitingJobsCount(queueName: string): Promise<number> {
  const jobs = await getWaitingJobs(queueName);
  return jobs.length;
}

export interface ObservedJob {
  id?: string;
  name?: string;
  data: unknown;
  opts?: JobsOptions;
}

export async function waitForJobs(
  queueName: string,
  expectedCount: number,
  timeoutMs = 5000
): Promise<ObservedJob[]> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const jobs = await getWaitingJobs(queueName);
    if (jobs.length >= expectedCount) {
      return jobs.map((job) => ({ id: job.id, name: job.name, data: job.data, opts: job.opts }));
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  const actual = await getWaitingJobsCount(queueName);
  throw new Error(`Timeout waiting for ${expectedCount} jobs in ${queueName}; found ${actual}`);
}

export async function clearQueue(queueName: string): Promise<void> {
  const queue = makeQueue(queueName);
  try {
    await queue.obliterate({ force: true });
  } finally {
    await queue.close();
  }
}