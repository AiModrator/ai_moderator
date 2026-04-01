import { chunking, chunkingForPolling } from "../helpers/helpers.js";
import { sourcePollingQueue } from "../queue/queue.js";
import { schedulerQueue } from "../queue/queue.js";
import { contentQueue } from "../queue/queue.js";










const REPEAT_INTERVAL = 30000;



export async function contentScheudler(content: any) {
    await sourcePollingQueue.add(
        'pollContentSource',
        {
            contentId: content.id,
            contentUrl: content.url,
            contentLastPolledAt: content.last_polled_at

        },
        {
            attempts: 5, // Retry 5 times
            backoff: {
                type: 'exponential',
                delay: 2000, // Initial delay of 2 seconds
            },
        }
    );
}




export const startPollingScheduler = async () => {
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







export async function contentScheduler(sourceId:number   ,  contents:any , maxTokens: number) {
    
    let  classifiedPosts = chunking(contents , maxTokens) ;
    
    console.log('contents', contents);
    console.log('classifiedPosts', classifiedPosts);
   
   
    for (const contents of classifiedPosts) {
        await contentQueue.add('processContent', {
            contents: contents,
            sourceId,
        });
    }
}





