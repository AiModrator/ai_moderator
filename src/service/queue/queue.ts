import Redis from 'ioredis';
import { Queue, Worker} from 'bullmq';
import {connectionRedis}  from '../../config/redis';

// We need to define a connection that is reused across all our queues and workers.
// This is important to avoid issues with Redis client limits and ensure efficient use of resources.

// Define our queues
export const forumPollingQueue = new Queue('forumPollingQueue', { connection :connectionRedis });
export const postProcessingQueue = new Queue('postProcessingQueue', { connection :connectionRedis });
export const schedulerQueue = new Queue('schedulerQueue', { connection: connectionRedis });

