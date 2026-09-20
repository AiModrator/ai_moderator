
import { createHash } from 'crypto';

import { connectionRedis } from '../../config/redis';
import { logsWrapperFactory } from '../../utils/wrappers';
import { Phase, Steps } from '@moderator/database';
import { ContentQueuItem } from '../../types/types';
import { stringify } from 'querystring';


const postHashMap = new Map<string, string[]>();

/**
 * Hashes post content to detect duplicates within a batch and across batches.
 * For now, uses a simple in-memory map as a cache.
 *
 * @param posts - A list of posts to check for spam.
 * @returns An array of objects, each containing a post ID and its duplicate count.
 */
export const detectSpamMain = async (contents: ContentQueuItem[], sourceId: number): Promise<{ idContent: string; duplicateCount: number }[]> => {

  const log = logsWrapperFactory( Steps.PROCESSING_SPAM , Phase.MODERATION, sourceId);
  const detectSpamWithLogs = log(detectSpam);
  const spamResults = await detectSpamWithLogs(contents);
  return spamResults;

};




async function detectSpam(contents: ContentQueuItem[]): Promise<{ idContent: string; duplicateCount: number }[]> {
  let spamResults: { idContent: string; duplicateCount: number }[] = [];

  for (const content of contents) {
    const contentResult = await spamValidator(content);
    spamResults.push(contentResult);
  }
  return spamResults;
};




async function spamValidator(contentItem: ContentQueuItem): Promise<{ idContent: string; duplicateCount: number }> {
  const keys = await connectionRedis.keys('content:*'); // Récupère toutes les clés de posts

  const hashContent = createHash('sha256').update(contentItem.content || '').digest('hex');

  for (const key of keys) {
    const stockedContent = await connectionRedis.hgetall(key);

    if (stockedContent.contentHasher === hashContent) {
      await connectionRedis.hset(key, 'retry', stockedContent.retry + 1);
      return {
        idContent: `${contentItem.id}`  ,
        duplicateCount: Number(stockedContent.retry) + 1
      }
    }

  }
  const key = "post:" + contentItem.id; 


  await connectionRedis.hset(key, {
    contentHasher: hashContent,
    retry: 0
  });
  // Expire le post apres 1 jour
  await connectionRedis.expire(key, 1 * 24 * 60 * 60);
  return {
    idContent :`${contentItem.id}`,
    duplicateCount: 1
  }
}
