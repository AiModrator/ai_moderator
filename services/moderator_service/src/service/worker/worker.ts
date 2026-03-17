import { Worker, Job } from 'bullmq';
import {  schedulerQueue, forumPollingQueue, contentQueue } from '../queue/queue';
import { connectionRedis } from '../../config/redis';
import { forumPollingSchedulerWorker, postScheduler } from '../triggers/trigger';
import { classifiePosts } from '../../utils/tokenIconemizer';
import { getFormByIdExperience, updateForumAfterPolling, updateForumOnNoNewPosts, updateForumOnPollingFailure } from '../../models/forum';
import { Post } from '../../types/types';
import { getRisksForForum } from '../../models/regle';

// Imports for the post-processing pipeline
import { detectSpamMain } from '../post-processing/spam';
import { resolveUserPolicy } from '../post-processing/policy';
import { processLanguageMain } from '../post-processing/language';
import { preprocessContentMain } from '../post-processing/preprocessor';
import { callAiMain } from '../post-processing/inference';
import { divideList } from '../../utils/listUtils';


// ! Verifier que les retry et les backoff sont bien configurés
export const startAllWorkers = (whopClient: any , aiTransaltoreClient: any , aiModerationClients: any) => {
    setupSchedulerWorker();
    setupForumPollingWorker(whopClient);
    setupPostProcessingWorker(aiTransaltoreClient , aiModerationClients);
};

// Worker for the scheduler queue
export const setupSchedulerWorker = () => {
    new Worker(

        schedulerQueue.name,
        async (job) => {
            await forumPollingSchedulerWorker(job);
        },
        { connection : connectionRedis }


    );
    console.log(`Worker for queue ${schedulerQueue.name} started.`);
};



//____________________________________________________________________________________________________________________
//-Worker
// Worker for the forum polling queue


// Worker for the post processing queue
export const setupPostProcessingWorker = (aiTransaltoreClient: any , aiModerationClients: any) => {
    new Worker(
        contentQueue.name,
        async (job: Job) => {
            const { postList, forumId } = job.data as { postList: Post[], forumId: string };
            console.log(`Processing post batch for forum ${forumId}. Batch size: ${postList.length}`);

            try {
                // 1. Spam Detection
                const spamResults = await detectSpamMain(postList , forumId);
                console.log('Spam detection results:', spamResults);

                // 2. User Policy Resolution
                
                const policy = await resolveUserPolicy(forumId, getRisksForForum , getFormByIdExperience);

                // 3. Language Processing
                const translatedPosts = await processLanguageMain(postList ,policy.formLanguage , forumId, aiTransaltoreClient);

                // 4. ,  Content Preprocessing
                const preprocessedPosts = await preprocessContentMain( forumId  , translatedPosts );

                // 5. Prompt Building
                const promptPayload = {
                    forumId , 
                    normalizedContents: preprocessedPosts,
                    risks: policy.risks,
                    forumContext: policy.formDescrition,
                };
                // const aiPrompt = await buildPrompt(promptPayload);
                // console.log('AI prompt built.');

                // 6. AI Inference
                const aiResult = await callAiMain(promptPayload , aiModerationClients);
                console.log('AI inference complete:', aiResult);
                
                if (job.opts.attempts) {
                    if (job.attemptsMade + 1 >= job.opts.attempts) {
                        
                    }

                }
                // TODO: Send result to the next queue

            } catch (error) {
                console.error(`Error processing post batch for forum ${forumId}:`, error);
                const [firstHalf, secondHalf] = divideList(postList); 

                await contentQueue.add('processPost', { postList: firstHalf, forumId }, {
                    attempts: 5,
                    backoff: { type: 'exponential', delay: 1000 },
                });
                await contentQueue.add('processPost', { postList: secondHalf, forumId }, {
                    attempts: 5,
                    backoff: { type: 'exponential', delay: 1000 },
                });
                throw error; // Ensure the original job fails
            }
        },
        { 
            connection : connectionRedis,
            concurrency: 5 // Process 5 jobs concurrently
        }
    );
    console.log(`Worker for queue ${contentQueue.name} started.`);
};

