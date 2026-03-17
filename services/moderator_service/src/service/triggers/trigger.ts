import { Job } from 'bullmq';
import { forumPollingQueue, contentQueue, schedulerQueue } from '../queue/queue';
import { getForumsToPoll } from '../../models/forum';
import { Post } from '../../types/types';

const  REPEAT_INTERVAL = 30000;
const BATCH_SIZE = 10; // Number of forums to process in each batch


export const setupForumPollingScheduler = async () => {
    // Add a repeatable job to the schedulerQueue
    await schedulerQueue.add(
        'forumPollingScheduler',
        {},
        {
            repeat: {
                every: REPEAT_INTERVAL, // Repeat every 30 seconds
            },
        }
    );

    console.log('Forum polling scheduler set up.');
};



export async function postScheduler(classifiedPosts: Post[][], forumId: string) {

    for (const postList of classifiedPosts) {
        await contentQueue.add('processPost', {
            postList: postList,
            forumId,
        });
    }
}
