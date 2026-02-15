import Redis from 'ioredis';
import { Queue, Worker} from 'bullmq';


// We need to define a connection that is reused across all our queues and workers.
// This is important to avoid issues with Redis client limits and ensure efficient use of resources.
export const connection = {
  host: 'localhost',
  port: 6379
};;

// Define our queues
export const forumPollingQueue = new Queue('forumPollingQueue', { connection });
export const postProcessingQueue = new Queue('postProcessingQueue', { connection });
export const schedulerQueue = new Queue('schedulerQueue', { connection });

