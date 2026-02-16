import { Worker } from 'bullmq';
import { connection, schedulerQueue, forumPollingQueue, postProcessingQueue } from '../queue/queue';
import { forumPollingSchedulerWorker } from './scheduler';
import {prisma} from '../../config/prismaClient';
import { classifiePosts } from '../../utils/tokenIconemizer';

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

// Worker for the forum polling queue
export const setupForumPollingWorker = (whopClient: any) => {
    new Worker(
        forumPollingQueue.name,
        async (job) => {
            const { forumId , forumExperienceId , forumLastExternalPostId} = job.data;
            console.log(`Processing pollForum job for forum: ${forumId}`);

            try {
            

                // 3. Récupérer les derniers posts.
                const newPosts = await whopClient.getNewPost(forumLastExternalPostId, forumExperienceId ) ;
                if (newPosts.length === 0) {
                    console.log(`No new posts for forum: ${forumId}`);
                    // Mettre à jour last_polled_at même s'il n'y a pas de nouveaux posts
                    await prisma.forum.update({
                        where: { id: forumId },
                        data: {
                            last_polled_at: new Date(),
                            polling_failed: false,
                            last_polling_error: null,
                        },
                    });
                    return;
                }

                let lastExternalPostId = forumLastExternalPostId;
                const {classifiedPosts , unclassifiedPosts} = classifiePosts(newPosts , 10) ;
                // ! je doit presister unclassifiedPost dans la base de donne

                for (const postList of classifiedPosts) {
                    // 5. Pour chaque nouveau post : Ajouter un job dans post_queue.
                    await postProcessingQueue.add('processPost', {
                        postList : postList , 
                        forumId,// Pass relevant post data
                    });

                }

                  lastExternalPostId = newPosts.at(-1)?.id ;

                // 6. Mettre à jour en base :
                // last_polled_at = now()
                // last_external_post_id = id du dernier post traité
                await prisma.forum.update({
                    where: { id: forumId },
                    data: {
                        last_polled_at: new Date(),
                        last_external_post_id: lastExternalPostId,
                        polling_failed: false,
                        last_polling_error: null,
                    },
                });
                console.log(`Forum ${forumId} updated. Last external post ID: ${lastExternalPostId}`);
            } catch (error: any) {
                console.error(`Error processing pollForum job for forum ${forumId}:`, error);
                // Update polling_failed and last_polling_error on failure
                await prisma.forum.update({
                    where: { id: forumId },
                    data: {
                        polling_failed: true,
                        last_polling_error: error.message || 'Unknown error',
                    },
                });
                throw error; // Re-throw to trigger BullMQ's retry mechanism
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

export const startAllWorkers = (whopClient: any) => {
    setupSchedulerWorker();
    setupForumPollingWorker(whopClient);
    setupPostProcessingWorker();
};
