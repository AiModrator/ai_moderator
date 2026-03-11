import { Worker, Job } from 'bullmq';
import { schedulerQueue, forumPollingQueue, postProcessingQueue } from 'src/service/queue/queue';
import { connectionRedis } from 'src/config/redis';
import { forumPollingSchedulerWorker, postScheduler } from 'src/service/triggers/trigger';
import { classifiePosts } from 'src/utils/tokenIconemizer';
import { getFormByIdExperience, updateForumAfterPolling, updateForumOnNoNewPosts, updateForumOnPollingFailure } from 'src/models/forum';
import { Post } from 'src/types/types';
import { getRisksForForum } from 'src/models/regle';

// Imports for the post-processing pipeline
import { detectSpamMain } from 'src/service/post-processing/spam';
import { resolveUserPolicy } from 'src/service/post-processing/policy';
import { processLanguageMain } from 'src/service/post-processing/language';
import { preprocessContentMain } from 'src/service/post-processing/preprocessor';
import { callAiMain } from 'src/service/post-processing/inference';
import { divideList } from 'src/utils/listUtils';


// ! Verifier que les retry et les backoff sont bien configurés
export const startAllWorkers = (whopClient: any, aiTransaltoreClient: any, aiModerationClients: any) => {
    setupSchedulerWorker();
    setupForumPollingWorker(whopClient);
    setupPostProcessingWorker(aiTransaltoreClient, aiModerationClients);
};

// Worker for the scheduler queue
export const setupSchedulerWorker = () => {
    new Worker(
        schedulerQueue.name,
        async (job) => {
            await forumPollingSchedulerWorker(job);
        },
        { connection: connectionRedis }


    );
    console.log(`Worker for queue ${schedulerQueue.name} started.`);
};



//______________________________________________________________________________________________________________
//-Worker
// Worker for the forum polling queue
export const setupForumPollingWorker = (whopClient: any) => {
    new Worker(
        forumPollingQueue.name,
        async (job) => {
            await pollForum(job.data, whopClient);
        },
        { connection: connectionRedis }
    );
    console.log(`Worker for queue ${forumPollingQueue.name} started.`);
};

async function pollForum(jobData: any, whopClient: any) {
    const { forumId, forumExperienceId, forumLastExternalPostId } = jobData;
    console.log(`Processing pollForum job for forum: ${forumId}`);

    try {
        const newPosts = await whopClient.getNewPost(forumLastExternalPostId, forumExperienceId);
        console.log(`Found ${newPosts.length} new posts for forum ${forumId}`);

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
export const setupPostProcessingWorker = (aiTransaltoreClient: any, aiModerationClients: any) => {
    new Worker(
        postProcessingQueue.name,
        async (job: Job) => {
            const { postList, forumId } = job.data as { postList: Post[], forumId: string };
            console.log(`Processing post batch for forum ${forumId}. Batch size: ${postList.length}`);

            try {
                // 1. Spam Detection
                const spamResults = await detectSpamMain(postList, forumId);
                console.log('Spam detection results:', spamResults);

                // 2. User Policy Resolution
                console.log('Resolving user policy...');
                console.log('forumId:', forumId);
                const policy = await resolveUserPolicy(forumId, getRisksForForum, getFormByIdExperience);

                // 3. Language Processing
                const translatedPosts = await processLanguageMain(postList, policy.formLanguage, forumId, aiTransaltoreClient);

                // 4. ,  Content Preprocessing
                const preprocessedPosts = await preprocessContentMain(forumId, translatedPosts);

                // 5. Prompt Building
                const promptPayload = {
                    forumId,
                    normalizedContents: preprocessedPosts,
                    risks: policy.risks,
                    forumContext: policy.formDescrition,
                };
                // const aiPrompt = await buildPrompt(promptPayload);
                // console.log('AI prompt built.');

                // 6. AI Inference
                const aiResult = await callAiMain(promptPayload, aiModerationClients);
                console.log('AI inference complete:', aiResult);

                if (job.opts.attempts) {
                    if (job.attemptsMade + 1 >= job.opts.attempts) {

                    }

                }
                // TODO: Send result to the next queue

            } catch (error) {
                const isLastAttempt = job.attemptsMade + 1 >= (job.opts.attempts || 1);

                if (isLastAttempt && postList.length > 1) {
                    console.log("Dernière tentative échouée, division du lot...");
                    const [firstHalf, secondHalf] = divideList(postList);
                    await postProcessingQueue.add('processPost',
                        { postList: firstHalf, forumId },
                        { attempts: 5, backoff: { type: 'exponential', delay: 2000 } }
                    );
                    await postProcessingQueue.add('processPost',
                        { postList: secondHalf, forumId },
                        { attempts: 5, backoff: { type: 'exponential', delay: 2000 } }
                    );

                    // On ne throw pas forcément ici, ou on throw pour marquer l'original comme "Failed"
                    // mais les petits prendront le relais.
                }

                throw error; // Laisse BullMQ 
            }
        },
        {
            connection: connectionRedis,
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
    //TODO je doit presister unclassifiedPost dans la base de donne
    await postScheduler(classifiedPosts, forumId);
    const lastExternalPostId = newPosts[newPosts.length - 1]?.id
    //TODO Update after polling doit etre a la  fin du pipline 
    await updateForumAfterPolling(forumId, lastExternalPostId);
    console.log(`Forum ${forumId} updated. Last external post ID: ${lastExternalPostId}`);
    console.log('✅ Classified posts ======>.', classifiedPosts);
}

async function handlePollingError(forumId: string, error: any) {
    console.error(`Error processing pollForum job for forum ${forumId}:`, error);
    await updateForumOnPollingFailure(forumId, error);
    throw error; // Re-throw to trigger BullMQ's retry mechanism
}