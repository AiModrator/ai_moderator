import { contentQueue, schedulerQueue, sourcePollingQueue } from "../../src/service/queue/queue.js";

export interface QueueInspection {
  totalCount: number;
  jobs: Array<{
    id: string;
    name: string;
    status: string;
    progress: number | null;
    data: unknown;
    result: unknown;
    failedReason?: string;
  }>;
}

/**
 * Inspecte la queue contentQueue et retourne les statistiques et les jobs
 */
export async function inspectContentQueue(): Promise<any> {

  // Récupère les jobs par statut
  const waitingJobs = await contentQueue.getJobs(["waiting"], 0, -1);
  const activeJobs = await contentQueue.getJobs(["active"], 0, -1);
  const completedJobs = await contentQueue.getJobs(["completed"], 0, -1);
  const failedJobs = await contentQueue.getJobs(["failed"], 0, -1);

  const allJobs = [...waitingJobs, ...activeJobs, ...completedJobs, ...failedJobs];

  const jobs = allJobs.map((job) => ({
    id: job.id || "",
    name: job.name,
    data: job.data,
    result: job.returnvalue,
    failedReason: job.failedReason,
  }));

  return {  jobsCount: allJobs.length, jobs };
}



export async function inspectSourceContentQueue(): Promise<any> {

  // Récupère les jobs par statut
  const waitingJobs = await sourcePollingQueue.getJobs(["waiting"], 0, -1);
  const activeJobs = await sourcePollingQueue.getJobs(["active"], 0, -1);
  const completedJobs = await sourcePollingQueue.getJobs(["completed"], 0, -1);
  const failedJobs = await sourcePollingQueue.getJobs(["failed"], 0, -1);

  const allJobs = [...waitingJobs, ...activeJobs, ...completedJobs, ...failedJobs];

  const jobs = allJobs.map((job) => ({
    id: job.id || "",
    name: job.name,
    data: job.data,
    result: job.returnvalue,
    failedReason: job.failedReason,
  }));

  return {  jobsCount: allJobs.length, jobs };
}

/**
 * Retourne le nombre d'éléments en attente dans contentQueue
 */
export async function getContentQueueCount(): Promise<number> {
  const waitingCount = await contentQueue.getWaitingCount();
  return waitingCount;
}

/**
 * Vide la queue contentQueue (utile pour les tests)
 */
export async function clearContentQueue(): Promise<void> {
  await contentQueue.clean(0,1000, "completed");
  await contentQueue.clean(0,1000, "failed");
  await contentQueue.drain();
}

/**
 * Retourne les jobs en attente dans contentQueue
 */
export async function getWaitingJobs(): Promise<Array<unknown>> {
  const jobs = await contentQueue.getJobs(["waiting"], 0, -1);
  return jobs.map((job) => ({ id: job.id, data: job.data }));
}




/**
 * Supprime tous les jobs (en attente, retardés, actifs, etc.) 
 * de toutes les queues définies.
 */
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