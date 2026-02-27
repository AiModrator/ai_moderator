import { AiModerationClient, AiModerationClients } from "../../types/types";
import { PreprocessedPost } from "./preprocessor";
import {postProcessingLogs} from '../../Logs/PostLogs';

  interface AIResponse {
    rawResponse: string;
    parsedResult: any; // In a real scenario, this would be a structured type
    confidenceScore: number;
  }



  export  const  callAiMain = async  (promptPayload: any , aiModerationClients: AiModerationClients ) =>{

                const log = postProcessingLogs(promptPayload.formId, 'PROCESSING_AI_CALL');
                  const callAiWithLog =  log(callAI);
                  const aiResponse = await callAiWithLog(promptPayload , aiModerationClients)
                  return aiResponse
              }


 
   const callAI = async (promptPayload: any 
              , aiModerationClients: AiModerationClients 
              ) => {

        const risks = promptPayload.risks;
        const moderators = await selectModerator(risks, promptPayload.forumContext, aiModerationClients);
        const resultModeration = await excuteModerators(moderators, promptPayload.normalizedContents);
        return resultModeration
        
  };
  


 function selectModerator (risks : string[] , desription:string ,aiModerationClients : AiModerationClients  ):AiModerationClient[] {

  let moderators : AiModerationClient[] = [] ;
  for (const risk of risks){
    for (const moderator of aiModerationClients.moderators){
    if (risk in moderator.risks &&  !moderators.includes(moderator)){ {
      moderators.push(moderator)
    }
    } 
  }


}
return moderators ;
}



//* Ici si une requete a echouer tous les autre vont echouer aussi 
//* cette fonction n'est pas adapter encore pour  les risk personalisees
async function excuteModerators(moderators:AiModerationClient[] , normalizedContents:PreprocessedPost[]  ):Promise<| PreprocessedPost[] | undefined> {
  try{
    const results:any[] = []
    normalizedContents.forEach((content, index) => {
        results.push(
          { 
            postId: content.postId
          }
        )
      })
    for (const moderator of moderators){
      
      const  moderationPromess =  normalizedContents.map(content => moderator.getModeration(content.contentNormaliser));
      const responses = await  Promise.all(moderationPromess);

      responses.forEach((response, index) => {
        results[index] = {
          ...results[index] , 
           ...response 
        }
      })
    }

  }catch (error){
    return normalizedContents ;
  }
}

