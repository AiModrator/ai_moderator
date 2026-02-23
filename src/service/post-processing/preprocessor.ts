
interface TranslatedPost {
    postId: string;
    content: string;
  }
  
  interface PreprocessedPost {
    postId: string;
    contentNormaliser: string;
  }
  
  /**
   * Preprocesses content by normalizing and cleaning it.
   *
   * @param translatedPosts - A list of posts that have been through language processing.
   * @returns A list of posts with normalized content.
   */
  export const preprocessContent = async (
    translatedPosts: TranslatedPost[]
  ): Promise<PreprocessedPost[]> => {
    return translatedPosts.map(post => ({
      postId: post.postId,
      contentNormaliser: post.content.trim().toLowerCase(),
    }));
  };
  