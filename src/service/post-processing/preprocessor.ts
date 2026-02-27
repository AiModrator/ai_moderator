import {postProcessingLogs} from '../../Logs/PostLogs';

interface TranslatedPost {
    postId: string;
    content: string;
  }
export  interface PreprocessedPost {
    postId: string;
    contentNormaliser: string;
  }

  /**
   * Removes HTML tags from content.
   *
   * @param content - The content with potential HTML tags.
   * @returns Content without HTML tags.
   */
  const removeHtmlTags = (content: string): string => {
    return content.replace(/<[^>]*>/g, '');
  };

  /**
   * Standardizes content case to lowercase.
   *
   * @param content - The content to standardize.
   * @returns Lowercase content.
   */
  const standardizeCase = (content: string): string => {
    return content.toLowerCase();
  };

  /**
   * Removes URLs from content.
   *
   * @param content - The content with potential URLs.
   * @returns Content without URLs.
   */
  const removeUrls = (content: string): string => {
    return content.replace(/https?:\/\/[^\s]+|www\.[^\s]+/g, '');
  };
  
  /**
   * Preprocesses content by normalizing and cleaning it.
   *
   * @param translatedPosts - A list of posts that have been through language processing.
   * @returns A list of posts with normalized content.
   */
   const preprocessContent = async (
    translatedPosts: TranslatedPost[]
  ): Promise<PreprocessedPost[]> => {
    return translatedPosts.map(post => {
      let normalized = post.content;
      normalized = removeHtmlTags(normalized);
      normalized = removeUrls(normalized);
      normalized = standardizeCase(normalized);
      normalized = normalized.trim();
      
      return {
        postId: post.postId,
        contentNormaliser: normalized,
      };
    });
  };


  export const preprocessContentMain  = async ( formId : string  , 
    translatedPosts: TranslatedPost[]
  ): Promise<PreprocessedPost[]> => {

    const log = postProcessingLogs(formId, 'PROCESSING_CONTENT' );
  const preprocessContentWithLogs =  log(preprocessContent);
  const response = await preprocessContentWithLogs(translatedPosts );
  return response ; 
  }
