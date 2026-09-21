/**
 * BullMQClient — wrapper autour du producteur BullMQ.
 * Crée/réutilise une instance de `Queue` par nom de queue (pas de nouvelle
 * connexion Redis à chaque appel) et applique les options de retry/backoff
 * par défaut du service si aucune option n'est fournie explicitement.
 */

import { Queue, Job, JobsOptions, ConnectionOptions } from 'bullmq';
import { QueueError } from '../types/errors.js';

export interface BullMQClientOptions {
  defaultAttempts?: number;
  defaultBackoffMs?: number;
}

export class BullMQClient {
  private readonly queues = new Map<string, Queue>();
  private readonly connection: ConnectionOptions;
  private readonly defaultAttempts: number;
  private readonly defaultBackoffMs: number;

  constructor(connection: ConnectionOptions, options: BullMQClientOptions = {}) {
    this.connection = connection;
    this.defaultAttempts = options.defaultAttempts ?? 1;
    this.defaultBackoffMs = options.defaultBackoffMs ?? 1000;
  }

  async addJob(
    queueName: string,
    payload: object,
    options?: JobsOptions,
    jobName: string = 'default'
  ): Promise<Job> {
    try {
      const queue = this.getQueue(queueName);
      const jobOptions = options ?? this.defaultJobOptions();
      return await queue.add(jobName, payload, jobOptions);
    } catch (error) {
      throw new QueueError(readErrorMessage(error, `addJob(${queueName})`));
    }
  }

  async countJobs(queueName: string, statuses: Array<'waiting' | 'active' | 'completed' | 'failed' | 'delayed'>): Promise<number> {
    const queue = this.getQueue(queueName);
    const jobs = await queue.getJobs(statuses as never, 0, -1);
    return jobs.length;
  }

  getQueues(): Map<string, Queue> {
    return this.queues;
  }

  private getQueue(queueName: string): Queue {
    let queue = this.queues.get(queueName);
    if (!queue) {
      queue = new Queue(queueName, { connection: this.connection });
      this.queues.set(queueName, queue);
    }
    return queue;
  }

  private defaultJobOptions(): JobsOptions {
    const options: JobsOptions = {
      attempts: this.defaultAttempts,
      removeOnComplete: true,
    };
    if (this.defaultBackoffMs > 0) {
      options.backoff = {
        type: 'exponential',
        delay: this.defaultBackoffMs,
      };
    }
    return options;
  }
}

function readErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message;
  return `unknown ${fallback} error`;
}