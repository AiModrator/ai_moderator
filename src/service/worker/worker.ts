import { Worker } from 'bullmq';
import { connection, schedulerQueue, forumPollingQueue, postProcessingQueue } from '../queue/queue';
import { forumPollingSchedulerWorker, postScheduler } from '../triggers/trigger';
import { classifiePosts } from '../../utils/tokenIconemizer';
import { updateForumAfterPolling, updateForumOnNoNewPosts, updateForumOnPollingFailure } from '../../models/forum';
import { Post } from '../../types/types';



// ! Verifier que les retry et les backoff sont bien configurés
export const startAllWorkers = (whopClient: any) => {
    setupSchedulerWorker();
    setupForumPollingWorker(whopClient);
    setupPostProcessingWorker();
};

// Worker for the scheduler queue
export const setupSchedulerWorker = () => {
    new Worker(
        schedulerQueue.name,
        async (job) => {
            await forumPollingSchedulerWorker(job);
        },
        { connection }


    );
    console.log(`Worker for queue ${schedulerQueue.name} started.`);
};



//____________________________________________________________________________________________________________________
//-Worker
// Worker for the forum polling queue
export const setupForumPollingWorker = (whopClient: any) => {
    new Worker(
        forumPollingQueue.name,
        async (job) => {
            const { forumId, forumExperienceId, forumLastExternalPostId } = job.data;
            console.log(`Processing pollForum job for forum: ${forumId}`);

            try {
                const newPosts = await whopClient.getNewPost(forumLastExternalPostId, forumExperienceId);

                if (newPosts.length === 0) {
                    await handleNoNewPosts(forumId);
                    return;
                }

                await processNewPosts(newPosts, forumId);
            } catch (error: any) {
                await handlePollingError(forumId, error);
            }
        },
        { connection }
    );
    console.log(`Worker for queue ${forumPollingQueue.name} started.`);
};



// Worker for the post processing queue (placeholder)
export const setupPostProcessingWorker = () => {
    new Worker(
        postProcessingQueue.name,
        async (job) => {
            const { postId, forumId, postContent } = job.data;
            console.log(`Processing post ${postId} from forum ${forumId}. Content: ${postContent}`);
            // TODO: Implement actual post processing logic here
            // This is a placeholder for the next phase of the moderation system.
            console.log(`Post ${postId} processed (placeholder).`);
        },
        { connection }
    );
    console.log(`Worker for queue ${postProcessingQueue.name} started.`);
};



//____________________________________________________________________________________________________________________
//-Hnadler 
async function handleNoNewPosts(forumId: string) {
    console.log(`No new posts for forum: ${forumId}`);
    await updateForumOnNoNewPosts(forumId);
}



async function processNewPosts(
    newPosts: Post[],
    forumId: string,
) {
    const { classifiedPosts, unclassifiedPosts } = classifiePosts(newPosts, 10);
    // ! je doit presister unclassifiedPost dans la base de donne
    await  postScheduler(classifiedPosts, forumId);
    const lastExternalPostId = newPosts[newPosts.length - 1]?.id
    await updateForumAfterPolling(forumId, lastExternalPostId);
    console.log(`Forum ${forumId} updated. Last external post ID: ${lastExternalPostId}`);
}

async function handlePollingError(forumId: string, error: any) {
    console.error(`Error processing pollForum job for forum ${forumId}:`, error);
    await updateForumOnPollingFailure(forumId, error);
    throw error; // Re-throw to trigger BullMQ's retry mechanism
}