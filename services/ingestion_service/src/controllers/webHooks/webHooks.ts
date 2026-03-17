import { postScheduler } from "src/service/triggres/contentSchduler.js";





//TODO  : Je doit implmenter la journalisation

export async function postContent (req:any, res: any) {

    const source = req.ContentSource ;
    const contents = req.body.data.contents 

    // TODO :  Probleme du last updated et webhook
    await  postScheduler(source.id , contents , source.max_tokens)

}












