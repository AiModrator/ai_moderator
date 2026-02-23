
interface AIPrompt {
    prompt: string;
    expectedFormat: 'json';
  }
  
  interface AIResponse {
    rawResponse: string;
    parsedResult: any; // In a real scenario, this would be a structured type
    confidenceScore: number;
  }
  
  /**
   * Mock function to simulate calling an AI inference model.
   *
   * @param promptAi - The prompt to send to the AI.
   * @returns A mock response from the AI.
   */
  export const callAI = async (promptAi: AIPrompt): Promise<AIResponse[]> => {
    console.log('--- Mock AI Call ---');
    console.log('Prompt:', promptAi.prompt);
    console.log('--------------------');
  
    // Simulate a successful response for a few posts
    const mockParsedResult = [
      { postId: 'p1', detectedRisks: ['Spam'], confidence: 0.95 },
      { postId: 'p2', detectedRisks: [], confidence: 0.99 },
    ];
  
    return [
      {
        rawResponse: JSON.stringify(mockParsedResult),
        parsedResult: mockParsedResult,
        confidenceScore: 0.97,
      },
    ];
  };
  