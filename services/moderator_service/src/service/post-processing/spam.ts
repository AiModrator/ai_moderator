
import { createHash } from 'crypto';
import {postProcessingLogs} from '../../Logs/PostLogs';
import { connectionRedis } from '../../config/redis';
import { Post } from '../../../../generated/browser';

const postHashMap = new Map<string, string[]>();

/**
 * Hashes post content to detect duplicates within a batch and across batches.
 * For now, uses a simple in-memory map as a cache.
 *
 * @param posts - A list of posts to check for spam.
 * @returns An array of objects, each containing a post ID and its duplicate count.
 */
export const detectSpamMain  = async (
  posts: Post[] , formId :string 
): Promise<{ idPost: string; duplicateCount: number }[]> => {

  const log = postProcessingLogs(formId, 'PROCESSING_SPAM');
  const detectSpamWithLogs =  log(detectSpam);
  const spamResults = await detectSpamWithLogs(posts);
   return spamResults;
};

 


async function detectSpam(
  posts: Post[]
): Promise<{ idPost: string; duplicateCount: number }[]> {
  let  spamResults: { idPost: string; duplicateCount: number }[] = [];
 
  for (const post of posts) {
    const postResult = await spamValidator(post);
    spamResults.push(postResult);
  }
  return spamResults;
};




async function spamValidator(post : Post):Promise<{ idPost: string; duplicateCount: number }> {
    const keys = await connectionRedis.keys('post:*'); // Récupère toutes les clés de posts

    const hashContent =  createHash('sha256').update(post.content || '').digest('hex') ; 

    for (const key of keys) {
        const StockerPost = await connectionRedis.hgetall(key);

        if (StockerPost.contentHasher === hashContent) {
             await connectionRedis.hset(key, 'retry', StockerPost.retry + 1);
             return{ 
                idPost : post.id,
                duplicateCount : Number(StockerPost.retry) + 1
             }
        }

    }
    const key = "post:" + post.id;
    

    await connectionRedis.hset(key, {
            contentHasher: hashContent,
            first_post_date: post.created_at,
            retry: 0
        });
            // Expire le post apres 1 jour
             await connectionRedis.expire(post.id, 1* 24 * 60 * 60);
             return{ 
                idPost : post.id,
                duplicateCount : 1
             }
}
