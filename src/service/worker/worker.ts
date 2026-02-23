import { Worker, Job } from 'bullmq';
import { connection, schedulerQueue, forumPollingQueue, postProcessingQueue } from '../queue/queue';
import { forumPollingSchedulerWorker, postScheduler } from '../triggers/trigger';
import { classifiePosts } from '../../utils/tokenIconemizer';
import { updateForumAfterPolling, updateForumOnNoNewPosts, updateForumOnPollingFailure } from '../../models/forum';
import { Post } from '../../types/types';
import { getRisksForForum } from '../../models/regle';

// Imports for the post-processing pipeline
import { detectSpam } from '../post-processing/spam';
import { resolveUserPolicy } from '../post-processing/policy';
import { processLanguage } from '../post-processing/language';
import { preprocessContent } from '../post-processing/preprocessor';
import { buildPrompt } from '../post-processing/promptBuilder';
import { callAI } from '../post-processing/inference';


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
            await pollForum(job.data, whopClient);
        },
        { connection }
    );
    console.log(`Worker for queue ${forumPollingQueue.name} started.`);
};

async function pollForum(jobData: any, whopClient: any) {
    const { forumId, forumExperienceId, forumLastExternalPostId } = jobData;
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
}


// Worker for the post processing queue
export const setupPostProcessingWorker = () => {
    new Worker(
        postProcessingQueue.name,
        async (job: Job) => {
            const { postList, forumId } = job.data as { postList: Post[], forumId: string };
            console.log(`Processing post batch for forum ${forumId}. Batch size: ${postList.length}`);

            try {
                // 1. Spam Detection
                const spamResults = await detectSpam(postList);
                console.log('Spam detection results:', spamResults);

                // 2. User Policy Resolution
                const policy = await resolveUserPolicy(forumId, getRisksForForum);
                console.log('User policy resolved.');

                // 3. Language Processing
                const translatedPosts = await processLanguage(postList);
                console.log('Language processing complete.');

                // 4. Content Preprocessing
                const preprocessedPosts = await preprocessContent(translatedPosts);
                console.log('Content preprocessing complete.');

                // 5. Prompt Building
                const promptPayload = {
                    translatedContents: translatedPosts,
                    normalizedContents: preprocessedPosts,
                    risks: policy.risks,
                    forumContext: policy.forumContext,
                };
                const aiPrompt = await buildPrompt(promptPayload);
                console.log('AI prompt built.');

                // 6. AI Inference
                const aiResult = await callAI(aiPrompt);
                console.log('AI inference complete:', aiResult);
                
                // TODO: Send result to the next queue

            } catch (error) {
                console.error(`Error processing post batch for forum ${forumId}:`, error);

                // Re-queue posts individually on batch failure
                for (const post of postList) {
                    await postProcessingQueue.add('processPost', { postList: [post], forumId }, {
                        attempts: 5,
                        backoff: { type: 'exponential', delay: 1000 },
                    });
                }
                throw error; // Ensure the original job fails
            }
        },
        { 
            connection,
            concurrency: 5 // Process 5 jobs concurrently
        }
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