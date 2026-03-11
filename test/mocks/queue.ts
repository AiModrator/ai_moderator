
import { Queue } from './bullmq';

export const connection = { status: 'mock' };
export const forumPollingQueue = new Queue('forumPollingQueue');
export const postProcessingQueue = new Queue('postProcessingQueue');
export const schedulerQueue = new Queue('schedulerQueue');
