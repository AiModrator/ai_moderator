
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import { buildPrompt } from '../../../src/service/post-processing/promptBuilder';

describe('Prompt Builder', () => {
  it('should build a correctly structured prompt', async () => {
    const promptData = {
      translatedContents: [{ postId: 'p1', content: 'Original content' }],
      normalizedContents: [{ postId: 'p1', contentNormaliser: 'normalized content' }],
      risks: [{ risque: 'Test Risk', description: 'This is a test risk.' }],
      forumContext: 'This is the forum context.',
    };

    const result = await buildPrompt(promptData);

    deepStrictEqual(result.expectedFormat, 'json');
    // We can't check the exact prompt string because of whitespace, but we can check for key elements.
    if (!result.prompt.includes('normalized content')) {
        throw new Error('Prompt does not contain normalized content');
    }

    if (!result.prompt.includes('Test Risk')) {
        throw new Error('Prompt does not contain the risk');
    }

    if (!result.prompt.includes('This is the forum context.')) {
        throw new Error('Prompt does not contain the forum context');
    }

  });
});
