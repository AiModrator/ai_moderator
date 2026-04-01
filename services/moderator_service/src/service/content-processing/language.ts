import { Content, Phase, Steps } from "@moderator/database";
import { logsWrapperFactory } from "../../utils/wrappers";
import { ContentQueuItem } from "../../types/types";


export interface TranslatedPost {
  id: string | number;
  content: string;
}



export const processLanguageMain = async ( contents: ContentQueuItem[], forumLanguage: string, sourceId: number,  translator_client: any): Promise<TranslatedPost[]> => {

  const log =logsWrapperFactory(Phase.MODERATION, Steps.PROCESSING_SPAM, sourceId);
  const processLanguagewithLogs = log(processLanguage);
  const response = await processLanguagewithLogs(contents, forumLanguage, translator_client);
  return response
}



 const processLanguage = async (contents: ContentQueuItem[] , forumLanguage : string ,  translator_client  : any  ): Promise<TranslatedPost[]>  => {

  const translatedPosts: TranslatedPost[] = [] ;

  if(forumLanguage.trim().toUpperCase() !== 'EN'){
    const ai_input =  promptBuilder(contents) ;
    const ai_output = await  ai_translotor(ai_input , translator_client) ;
    const ai_content = outputParser(ai_output) ;
    for( const content of ai_content){
      translatedPosts.push({ id: content.id, content: content.content || "" }) ;
    } 

  }
  for( const content of contents){
    translatedPosts.push({ id: content.id, content: content.content || "" }) ;
  } 

  return translatedPosts;
};





async function ai_translotor(input: string | string[] , translator_client : any){
  const response = await translator_client.post('', {
    inputs: input,})

    return response.data
}

export const promptBuilder  = (contents: ContentQueuItem[]) => {
  return contents.map(content => `${content.id}: ${content.content}`);
};


export const outputParser = (stringContent :string | string[]): TranslatedPost[] => {

  if(Array.isArray(stringContent)){
     return  stringTableToTranslatedPost(stringContent)
    
  }
  else{
     return stringToTranslatedPost(stringContent)
     
  }
};


//TODO : A implementer selon  l'api utililser 
function stringToTranslatedPost(content : string): TranslatedPost[] {

  return [{
    id:'' , 
    content: ''
  }];
}


//TODO : A implementer selon  l'api utililser 
function stringTableToTranslatedPost(content : string[]): TranslatedPost[] {

  return [{
    id:'' , 
    content: ''
  }];
}



