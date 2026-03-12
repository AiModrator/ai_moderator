
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import { processLanguage } from '../../../src/service/post-processing/language';
import { Post } from '../../../src/types/types';

describe('Language Processor', () => {
  it('should act as a pass-through and return original content', async () => {
    const posts: Post[] = [
        { id: 'p1', content: 'This is a test post.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
        { id: 'p2', content: 'This is another test post.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
    ];

    const result = await processLanguage(posts);

    const expected = [
      { postId: 'p1', content: 'This is a test post.' },
      { postId: 'p2', content: 'This is another test post.' },
    ];

    deepStrictEqual(result, expected);
  });
});
