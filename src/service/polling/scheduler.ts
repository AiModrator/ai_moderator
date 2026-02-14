import { Job } from 'bullmq';
import { forumPollingQueue, schedulerQueue } from './queue';
import {prisma} from '../../config/prismaClient';

const BATCH_SIZE = 10; // Number of forums to process in each batch
const  REPEAT_INTERVAL = 30000;

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

export const forumPollingSchedulerWorker = async (job: Job) => {
    console.log(`Processing scheduler job: ${job.id}`);
    try {
        const forums = await prisma.forum.findMany({
            where: {
                polling_failed: false,
            },
            orderBy: {
                last_polled_at: 'asc',
            },
            take: BATCH_SIZE,
        });

        if (forums.length === 0) {
            console.log('No forums to poll.');
            return;
        }

        for (const forum of forums) {
            await forumPollingQueue.add(
                'pollForum',
                {
                    forumId: forum.id,
                    forumExperienceId: forum.experience_id,
                    forumLastExternalPostId: forum.last_external_post_id
                },
                {
                    attempts: 5, // Retry 5 times
                    backoff: {
                        type: 'exponential',
                        delay: 2000, // Initial delay of 2 seconds
                    },
                }
            );
            console.log(`Added pollForum job for forum: ${forum.id}`);
        }
    } catch (error) {
        console.error('Error in forum polling scheduler worker:', error);
        throw error;
    }
};
