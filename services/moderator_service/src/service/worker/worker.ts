import { Worker, Job } from 'bullmq';
import {   contentQueue } from '../queue/queue';
import { connectionRedis } from '../../config/redis';
import { ContentQueueData, ContentQueuItem, Post } from '../../types/types';


// Imports for the post-processing pipeline
import { detectSpamMain } from '../content-processing/spam';
import { processLanguageMain } from '../content-processing/language';
import { preprocessContentMain } from '../content-processing/preprocessor';
import { callAiMain } from '../content-processing/inference';
import { divideList } from '../../utils/listUtils';


// ! Verifier que les retry et les backoff sont bien configurés
export const startAllWorkers = (whopClient: any , aiTransaltoreClient: any , aiModerationClients: any) => {
  
    setupContentProcessingWorker(aiTransaltoreClient , aiModerationClients);
};





// Worker for the post processing queue
export const setupContentProcessingWorker = (aiTransaltoreClient: any , aiModerationClients: any) => {
    new Worker(
        contentQueue.name,
        async (job: Job) => {
            const { contents, sourceId } = job.data as ContentQueueData;
            console.log(`Processing post batch for forum ${sourceId}. Batch size: ${contents.length}`);
            
            try {
                // 1. Spam Detection
                processingPipline(job, contents, Number(sourceId) , aiTransaltoreClient , aiModerationClients);
             
            } catch (error) {
                console.error(`Error processing post batch for forum ${sourceId}:`, error);
                const [firstHalf, secondHalf] = divideList(contents); 

                await contentQueue.add('processPost', { postList: firstHalf, sourceId }, {
                    attempts: 5,
                    backoff: { type: 'exponential', delay: 1000 },
                });
                await contentQueue.add('processPost', { postList: secondHalf, sourceId }, {
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









const processingPipline = async ( job: Job , contents:ContentQueuItem[], sourceId: number , aiTranslotorclient: any , aiModerationClients : any)  => {

    // 1. Spam Detection
    const spamResults = await detectSpamMain(contents, sourceId);
    console.log('Spam detection results:', spamResults);

    // 2. User Policy Resolution

    // const policy = await resolveUserPolicy(forumId, getRisksForForum, getFormByIdExperience);
    const mockPolicy = {
        formDescrition: 'Mock forum description',
        formLanguage: 'en',
        risks :[

        ]
    }

    // 3. Language Processing
    const translatedPosts = await processLanguageMain(contents, mockPolicy.formLanguage, sourceId, aiTranslotorclient);

    // 4. ,  Content Preprocessing
    const preprocessedPosts = await preprocessContentMain(sourceId, translatedPosts);

    // 5. Prompt Building
    const promptPayload = {
        sourceId,
        normalizedContents: preprocessedPosts,
        risks: mockPolicy.risks,
        forumContext: mockPolicy.formDescrition,
    };
    // const aiPrompt = await buildPrompt(promptPayload);
    // console.log('AI prompt built.');

    // 6. AI Inference
    // const aiResult = await callAiMain(promptPayload, aiModerationClients);
    console.log('resultat final', promptPayload);

    if (job.opts.attempts) {
        if (job.attemptsMade + 1 >= job.opts.attempts) {
            
        }

    }
    // TODO: Send result to the next queue

}