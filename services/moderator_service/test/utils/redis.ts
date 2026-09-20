import { JobType } from "bullmq";
import { contentQueue, decisionQueue, schedulerQueue, sourcePollingQueue } from "../../src/service/queue/queue";
import { ContentQueuItem } from "../../src/types/types";







export const clearAllQueues = async () => {
  const queues = [contentQueue, schedulerQueue, sourcePollingQueue];

  try {
    console.log('--- Début du nettoyage des queues ---');

    const results = await Promise.all(queues.map(async (queue) => {
      // .obliterate({ force: true }) est radical : il supprime tout, 
      // y compris les métadonnées de la queue dans Redis.
      // Si vous voulez juste vider les jobs sans supprimer la queue :
      await queue.drain(true); // Supprime les jobs en attente et retardés
      await queue.clean(0, 1000, 'completed'); // Nettoie les jobs terminés
      await queue.clean(0, 1000, 'failed');    // Nettoie les jobs en échec
      
      return queue.name;
    }));

    console.log(`Succès : Les queues [${results.join(', ')}] ont été vidées.`);
  } catch (error) {
    console.error('Erreur lors du nettoyage des queues :', error);
  }
};





export async function addContentJobs(contents: ContentQueuItem[]  ,  sourceId: number  , number?: number ) {

     for (let i = 0; i < (number || 5); i++) {
        await contentQueue.add('processContent', {
            contents: contents,
            sourceId,
        });
    }
}



export async function getAllItemsFromDecisionQueue(): Promise<any[]> {

  const jobsType: JobType[]  =  [
  'active', 
  'waiting', 
  'completed', 
  'failed', 
  'delayed', 
  'paused'
]
  const jobs = await decisionQueue.getJobs(jobsType);
  const items = await Promise.all(jobs.map(job => job?.data));
  return items;
}

