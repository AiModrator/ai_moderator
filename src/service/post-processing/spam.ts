
import { createHash } from 'crypto';
import { Post } from '../../types/types';

import { redis } from '../config/redisClient';

const postHashMap = new Map<string, string[]>();

/**
 * Hashes post content to detect duplicates within a batch and across batches.
 * For now, uses a simple in-memory map as a cache.
 *
 * @param posts - A list of posts to check for spam.
 * @returns An array of objects, each containing a post ID and its duplicate count.
 */
export const detectSpam = async (
  posts: Post[]
): Promise<{ idPost: string; duplicateCount: number }[]> => {
  let  spamResults: { idPost: string; duplicateCount: number }[] = [];
 
  for (const post of posts) {
    const postResult = await spamValidator(post);
    spamResults.push(postResult);
  }
  return spamResults;
};





async function spamValidator(post : Post):Promise<{ idPost: string; duplicateCount: number }> {
    const keys = await redis.keys('post:*'); // Récupère toutes les clés de posts

    const hashContent =  createHash('sha256').update(post.content || '').digest('hex') ; 
   
    for (const key of keys) {
        const post = await redis.hgetall(key);

        if (post.contentHasher === hashContent) {
             await redis.hset(key, 'retry', post.retry + 1);
             return{ 
                idPost : post.id,
                duplicateCount : post.retry + 1
             }
        }

    }
    const key = "post:" + post.id;
    

    await redis.hset(key, {
            contentHasher: hashContent,
            first_post_date: post.created_at,
            retry: "0"
        });
            // Expire le post apres 1 jour
             await redis.expire(post.id, 1* 24 * 60 * 60);
             return{ 
                idPost : post.id,
                duplicateCount : 1
             }
}
