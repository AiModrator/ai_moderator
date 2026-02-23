
import { Post } from '../../types/types';

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
export const processLanguage = async (
  posts: Post[]
): Promise<TranslatedPost[]> => {
  const translatedPosts: TranslatedPost[] = posts
    .filter(post => post.content)
    .map(post => ({
        postId: post.id,
        content: post.content!,
    }));

  return translatedPosts;
};
