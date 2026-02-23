


interface Risk {
  risque: string;
  description: string;
}

interface Policy {
  risks: Risk[];
  forumContext: string;
}

/**
 * Resolves user policies by fetching standard and custom risks for a forum.
 *
 * @param forumId - The ID of the forum.
 * @returns An object containing the list of risks and a concatenated context string.
 */
export const resolveUserPolicy = async (
  forumId: string,
  getRisksForForum: (forumId: string) => Promise<any[]> // Assuming 'any[]' for now, adjust type as needed
): Promise<Policy> => {
  const regles = await getRisksForForum(forumId);
  const risks: Risk[] = [];
  let forumContext = '';

  for (const regle of regles) {
    if (regle.risque) {
      risks.push({
        risque: regle.risque.nom,
        description: regle.risque.description,
      });
      forumContext += `${regle.risque.description} `;
    }
    if (regle.customized_risque) {
      risks.push({
        risque: regle.customized_risque.nom,
        description: regle.customized_risque.description,
      });
      forumContext += `${regle.customized_risque.description} `;
    }
  }

  return {
    risks,
    forumContext: forumContext.trim(),
  };
};
