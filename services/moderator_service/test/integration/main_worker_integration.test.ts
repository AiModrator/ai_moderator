import { describe, it } from "node:test";
import { setupMainTest } from "../setup/setup";
import { addContentJobs } from "../utils/redis";
import { setupContentProcessingWorker } from "../../src/service/worker/worker";
import { sleep } from "../utils/utils";





describe("Main worker integration tests", () => {

    const context = setupMainTest()
    it("Doit traiter les posts Ajoutees ",async () => {

        console.log("Ajouter le contenu")
        await addContentJobs(context.data.contents, context.contentSource.id, 1)
        
        console.log("Lancer le worker")
        setupContentProcessingWorker(getMockTranslator() , getMockTranslator())

        await sleep(10000)

    })
})

















export function getMockTranslator() {
    return {
        post:  (url: string , data:any) => {
            return [
                'content1',
                'content2 ' , 
                'content3' , 
                'content4' 
            ]
        }
    }
}

