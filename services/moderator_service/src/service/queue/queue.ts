
import { Queue} from 'bullmq';
import { connectionRedis } from '../../config/redis';

// We need to define a connection that is reused across all our queues and workers.
// This is important to avoid issues with Redis client limits and ensure efficient use of resources.

export const contentQueue = new Queue('contentQueue', { connection :connectionRedis });
export const schedulerQueue = new Queue('schedulerQueue', { connection: connectionRedis });
export const sourcePollingQueue = new Queue('sourcePollingQueue', { connection :connectionRedis });
