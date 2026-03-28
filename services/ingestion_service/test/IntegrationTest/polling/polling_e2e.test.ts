import { describe, expect, it } from "vitest";
import { setupPollingTest, sleep } from "../../utils/setup";
import { connectionRedis } from "../../../src/config/RedisClient";
import { setupContentSourcePollingWorker , sourcePollingSchduler } from "../../../src/service/worker/worker";
import {inspectContentQueue, inspectSourceContentQueue} from '../../utils/queue'



describe("Polling Integration Tests", () => {
    // ✅ On garde l'objet complet
    const ctx = setupPollingTest();

    it("should add a jobs to queue", async () => {
        
        console.log("🚀 Setup workers du contentSource");
        setupContentSourcePollingWorker(ctx.mockAxiosClient , connectionRedis);
        await sourcePollingSchduler() ;

        console.log("Attendre 5 secondes");
        await sleep(5000);

        const  contentQueueData  = await inspectContentQueue();
        console.log("contentQueueData", contentQueueData);

        const sourceQueueData = await inspectSourceContentQueue();
        console.log("sourceQueueData", sourceQueueData);

        expect(contentQueueData.jobsCount).toBe(2);
        expect(sourceQueueData.jobsCount).toBe(1);

    } , 10000)}

)



