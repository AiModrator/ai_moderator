
import { Queue } from './bullmq';

export const connection = { status: 'mock' };
export const forumPollingQueue = new Queue('forumPollingQueue');
export const contentQueue = new Queue('contentQueue');
export const schedulerQueue = new Queue('schedulerQueue');
