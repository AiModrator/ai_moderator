import { startPollingScheduler } from "../../service/triggres/schdulers.js";
import { setupContentSourcePollingWorker, setupSchedulerWorker } from "../../service/worker/worker.js";







export async function setUpPolling(axiosFactory: any , connectionRedis : any) {
    
    
    setupSchedulerWorker(connectionRedis); ;
    setupContentSourcePollingWorker(axiosFactory , connectionRedis);

    // declencher le workflow
    await startPollingScheduler() ;
    
}