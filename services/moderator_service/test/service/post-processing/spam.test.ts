
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import { detectSpam } from '../../../src/service/post-processing/spam';
import { Post } from '../../../src/types/types';

describe('Spam Detector', () => {
  it('should detect duplicate posts and return correct duplicate counts', async () => {
    const posts: Post[] = [
      { id: 'p1', content: 'This is a test post.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
      { id: 'p2', content: 'This is another test post.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
      { id: 'p3', content: 'This is a test post.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
      { id: 'p4', content: 'Unique content.', forum_id: 'f1', created_at: new Date(), updated_at: new Date(), user_id:'1' },
    ];

    const result = await detectSpam(posts);

    // Expected: p1 and p3 are duplicates, so their count should be 2.
    // p2 and p4 are unique in this batch, but we need to check the global map.
    // Let's assume the map is fresh for this test.
    const expected = [
        { idPost: 'p1', duplicateCount: 2 },
        { idPost: 'p2', duplicateCount: 0 },
        { idPost: 'p3', duplicateCount: 2 },
        { idPost: 'p4', duplicateCount: 0 },
      ];
      

    deepStrictEqual(result.map(r => ({...r})).sort((a,b) => a.idPost.localeCompare(b.idPost)), expected.sort((a,b) => a.idPost.localeCompare(b.idPost)));
  });
});
