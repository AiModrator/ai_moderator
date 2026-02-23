
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import { callAI } from '../../../src/service/post-processing/inference';

describe('AI Inference Service', () => {
  it('should return a mock AI response', async () => {
    const prompt = {
      prompt: 'Test prompt',
      expectedFormat: 'json' as const,
    };

    const result = await callAI(prompt);

    // Check that the mock response is returned as expected
    deepStrictEqual(result[0].confidenceScore, 0.97);
    deepStrictEqual(result[0].parsedResult[0].postId, 'p1');
  });
});
