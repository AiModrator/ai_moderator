
import { describe, expect, it } from "vitest";
import { setupWebHooksTest } from "../../utils/setup";
import request from "supertest";
import { mockWebhookRequestPayload } from "../../utils/mock";
import app from '../../../src/config/express';
import { setupWebHooksRoutes } from "../../../src/controllers/webHooks/webHooks";

describe("Webhook Integration Tests", () => {
    // ✅ On garde l'objet complet
    const ctx = setupWebHooksTest(); 

    it("should trigger a webhook", async () => {
        // Au moment où on arrive ici, le beforeAll est fini.
        // On accède aux valeurs via 'ctx.'
        
        console.log("ID Source :", ctx.contentSource.id);
        const data = mockWebhookRequestPayload(ctx.contentSource.id);

        setupWebHooksRoutes(app);

        // ✅ On passe ctx.apiKey.key
        const response = await triggerWebhook(app, data, ctx.apiKey);
        
        console.log('Réponse du serveur:', response.status);
        expect(response.status).toBe(200);
    });
});

async function triggerWebhook(app:any , data:any , validToken:any) {
    console.log("key" , validToken)
    const response = await request(app)
        .post("/webhooks")
        .set('authorization', `${validToken}`)
        .set('Content-Type', 'application/json')
        .send({
            data : {...data}
        });
    return response;
}