
import { formState , createForumLog} from "../models/ForumLogs";

export  function postProcessingLogs(formId:string ,  step:formState ){

    return function (fnOrginal:Function){
        return async function(...args:any){
           try{
            const debut = performance.now();
            const response = await fnOrginal(...args)
            const fin = performance.now();
            await createForumLog({
                forumId: formId,
                state: step,
                isRetry: false,
                durationMs: fin - debut ,
              });
              return response  ;

           }catch(err : any ){

             await createForumLog({
                forumId: formId,
                state: step,
                isRetry: false,
                durationMs: 0,
                error: err instanceof Error ? err.message : String(err),
              });

            throw err
           }
    }
}  }