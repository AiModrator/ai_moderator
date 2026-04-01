import { Job, Worker } from "bullmq";
import { getContentSourceToPoll, updateSourceAfterPolling } from "../../models/contentSource.js";
import { contentScheduler, contentScheudler } from "../triggres/schdulers.js";
import { schedulerQueue, sourcePollingQueue } from "../queue/queue.js";

import { handlePollingError, processNewPosts } from "../helpers/helpers.js";
import { logsWrapperFactory } from "../../utils/wrappers.js";





const BATCH_SIZE = 10; // Number of forums to process in each batch




export const setupSchedulerWorker = (connectionRedis : any) => {
    new Worker(

        schedulerQueue.name,
        async (job) => {
            await sourcePollingSchduler();
        },
        { connection : connectionRedis }


    );
    console.log(`Worker for queue ${schedulerQueue.name} started.`);
};

export const setupContentSourcePollingWorker = (axiosFactory: any , connectionRedis : any) => {
    const logWrapper  = logsWrapperFactory('POLLING' , 'INGESTION'  )
    
    new Worker(
        sourcePollingQueue.name,
        async (job) => {
            const pollContentWithLog = logWrapper(pollContent)
            
            await pollContentWithLog(job.data, axiosFactory);
        },
        { connection  : connectionRedis}
    );
    console.log('Setup du worker pour la queue sourcePollingQueue');     
};










//  Fonction qui pull le contenu pour chaque contentSource 
async function pollContent(jobData: any, axiosFactory: any) {
    const { contentId , contentUrl , contentLastPolledAt } = jobData;
    console.log(`Polling  job for contentSourceId: ${contentId}`);

    try {
        //TODO : Securite 
        // TODO : verifier si il ya une erreur 
       let   contents = await axiosFactory.getAxiosClient(contentUrl).getNewContent(contentUrl, contentLastPolledAt);
       
       
        if (contents.length === 0) {
            return;
        }

        await processNewPosts(contents, contentId);
    } catch (error: any) {
        await handlePollingError(contentId, error.message);
    }
}















// worker liees au  schdulerQueue 
 export const sourcePollingSchduler = async () => {
    
    try {
        const sourceContents = await getContentSourceToPoll(BATCH_SIZE);

        if (sourceContents.length === 0) {
            console.log('No forums to poll.');
            return; 
        }
        for (const content of sourceContents) {
            await  contentScheudler(content);
            console.log(`Adde polling  job for source_ontent : ${content.id}`);
        }
    } catch (error) {
        console.error('Error in forum polling scheduler worker:', error);
        throw error;
    }
};

