
import { contentScheduler } from "../../service/triggres/schdulers.js";
import { errorWrapper, logsWrapperFactory } from "../../utils/wrappers.js";
import express from 'express';

import { validateApiKey } from "../middlewars/auth.js";
import { getSource, validateData } from "../middlewars/validator.js";
import { Phase, Steps } from "@ai-moderator/database";







export function setupWebHooksRoutes(app: any) {

    // Les middlewars
    app.use(express.json());
    
    app.use(validateApiKey);
    app.use('/webhooks', validateData);
    app.use('/webhooks', getSource);

    const logsWrappersfactory = logsWrapperFactory(Steps.WEBHOOK,Phase.INGESTION);

    app.post('/webhooks', errorWrapper(logsWrappersfactory(postContent)));


}








async function postContent(req: any, res: any) {

    const source = req.ContentSource;
    const contents = req.body.data.contents

    // TODO :  Probleme du last updated et webhook
    await contentScheduler(source.id, contents, source.max_tokens)

    res.status(200).json({ success: true });
}











