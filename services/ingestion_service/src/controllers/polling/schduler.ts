import { Job, Worker } from "bullmq";
import { get } from "node:http";
import { connectionRedis } from "src/config/RedisClient.js";
import { getDefaultSource } from "src/models/content.js";
import { getUserToPoll, updateForumOnPollingFailure, updateUserAfterPolling, updateUserWithNoContent } from "src/models/user.js";
import { schedulerQueue , userPollingQueue } from "src/service/queue/queue.js";
import { classifiePosts, postScheduler } from "src/service/triggres/contentSchduler.js";





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






export const userPollingSchduler = async (job: Job) => {
    console.log(`Processing scheduler job: ${job.id}`);
    try {
        const users = await getUserToPoll(BATCH_SIZE);

        if (users.length === 0) {
            console.log('No forums to poll.');
            return; 
        }

        for (const user of users) {
            await userPollingQueue.add(
                'pollUser',
                {
                    userId: user.id,
                    userUrl : user.url , 
                    userLastExternalPostId: user.last_external_post_id
                },
                {
                    attempts: 5, // Retry 5 times
                    backoff: {
                        type: 'exponential',
                        delay: 2000, // Initial delay of 2 seconds
                    },
                }
            );
            console.log(`Added userPolling job for forum: ${user.id}`);
        }
    } catch (error) {
        console.error('Error in forum polling scheduler worker:', error);
        throw error;
    }
};





//  Fonction qui pull le contenu pour chaque user
export const setupForumPollingWorker = (axiosClient: any) => {
    new Worker(
        userPollingQueue.name,
        async (job) => {
            await pollContent(job.data, axiosClient);
        },
        { connection  : connectionRedis}
    );
    console.log(`Worker for queue ${userPollingQueue.name} started.`);
};

async function pollContent(jobData: any, axiosClient: any) {
    const { userId , userUrl , userLastExternalPostId } = jobData;
    console.log(`Processing pollForum job for forum: ${userId}`);

    try {
        //TODO : Securite 
        let  {idSource , contents} = await axiosClient.getNewContent(userUrl, userLastExternalPostId);
        if(!idSource){
            idSource =  await getDefaultSource(userId)
        }
        if (contents.length === 0) {
            await updateUserWithNoContent(userId);
            return;
        }

        await processNewPosts(contents, userId  , idSource);
    } catch (error: any) {
        await handlePollingError(userId, error);
    }
}





async function processNewPosts(
    newContent: string[],
    userId: number,
    idSource : number
) {
    
    //TODO je doit presister unclassifiedPost dans la base de donne

    await  postScheduler(idSource,newContent, userId );
    await updateUserAfterPolling(userId);
 
}

async function handlePollingError(userId: string, error: any) {
    console.error(`Error processing pollForum job for user ${userId}:`, error);
    await updateForumOnPollingFailure(userId, error);
    throw error; // Re-throw to trigger BullMQ's retry mechanism
}