
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import { preprocessContent } from '../../../src/service/post-processing/preprocessor';

describe('Content Preprocessor', () => {
  it('should normalize content to lowercase and trim whitespace', async () => {
    const translatedPosts = [
      { postId: 'p1', content: '  This is a Test Post.  ' },
      { postId: 'p2', content: 'ANOTHER TEST POST' },
    ];

    const result = await preprocessContent(translatedPosts);

    const expected = [
      { postId: 'p1', contentNormaliser: 'this is a test post.' },
      { postId: 'p2', contentNormaliser: 'another test post' },
    ];

    deepStrictEqual(result, expected);
  });
});
