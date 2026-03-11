
import huggingFaceTranslatorClient from '../../config/ai_clients';
import { Post } from '../../../generated/browser';
import {postProcessingLogs} from '../../Logs/PostLogs';


interface TranslatedPost {
  postId: string;
  content: string;
}

/**
 * Processes the language of posts.
 * Currently a placeholder that assumes all content is in the target language (e.g., English).
 *
 * @param posts - A list of posts.
 * @returns A list of posts with their content, unchanged.
 */
export const processLanguageMain = async (
  posts: Post[], forumLanguage: string, formId: string,
  translator_client: any
): Promise<TranslatedPost[]> => {

  const log = postProcessingLogs(formId, 'PROCESSING_TRANSLATION');
  const processLanguagewithLogs = log(processLanguage);
  const response = await processLanguagewithLogs(posts, forumLanguage, translator_client);
  return response
}
 const processLanguage = async (
      posts: Post[] , forumLanguage : string , 
      translator_client  : any 
  ): Promise<TranslatedPost[]> => {

  const translatedPosts: TranslatedPost[] = [] ;

  if(forumLanguage.trim().toUpperCase() !== 'EN'){
    const ai_input =  promptBuilder(posts) ;
    const ai_output = await  ai_translotor(ai_input , translator_client) ;
    const ai_posts = outputParser(ai_output) ;
    for( const post of ai_posts){
      translatedPosts.push({ postId: post.postId, content: post.content || "" }) ;
    } 

  }
  for( const post of posts){
    translatedPosts.push({ postId: post.id, content: post.content || "" }) ;
  } 

  return translatedPosts;
};





async function ai_translotor(input: string | string[] , translator_client : any){
  const response = await translator_client.post('', {
    inputs: input,})

    return response.data
}

export const promptBuilder  = (posts: Post[]): string[] => {
  return posts.map(post => `${post.id}: ${post.content}`);
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
    postId:'' , 
    content: ''
  }];
}


//TODO : A implementer selon  l'api utililser 
function stringTableToTranslatedPost(content : string[]): TranslatedPost[] {

  return [{
    postId:'' , 
    content: ''
  }];
}



