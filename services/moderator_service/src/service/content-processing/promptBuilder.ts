
interface PromptBuilderInput {
    translatedContents: { postId: string; content: string }[];
    normalizedContents: { postId: string; contentNormaliser: string }[];
    risks: { risque: string; description: string }[];
    forumContext: string;
  }
  
  interface AIPrompt {
    prompt: string;
    expectedFormat: 'json';
  }
  
  /**
   * Builds a structured prompt for the AI model.
   *
   * @param data - An object containing all the necessary data to build the prompt.
   * @returns An object containing the final prompt and the expected format.
   */
  export const buildPrompt = async (
    data: PromptBuilderInput
  ): Promise<AIPrompt> => {
    // This is a simplified example. A real implementation would be more complex.
    const postContents = data.normalizedContents
      .map(p => `Post[${p.postId}]: ${p.contentNormaliser}`)
      .join('\\n');
  
    const riskSection = data.risks
      .map(r => `- ${r.risque}: ${r.description}`)
      .join('\\n');
  
    const prompt = `
  Analyze the following posts based on the provided context and risks.
  
  **Forum Context:**
  ${data.forumContext}
  
  **Risks to evaluate:**
  ${riskSection}
  
  **Posts to analyze:**
  ${postContents}
  
  For each post, provide a JSON object with the detected risks and a confidence score.
  Example: {"postId": "p1", "detectedRisks": ["Spam"], "confidence": 0.9}
  `;
  
    return {
      prompt,
      expectedFormat: 'json',
    };
  };
  