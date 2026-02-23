
import { prisma } from '../config/prismaClient';

/**
 * Retrieves all rules (standard and custom) for a given forum ID.
 *
 * @param forumId - The ID of the forum.
 * @returns A list of rules with their associated risk details.
 */
export async function getRisksForForum(forumId: string) {
  const regles = await prisma.regle.findMany({
    where: {
      forum_id: forumId,
    },
    include: {
      risque: true, // Include the related standard risk
      customized_risque: true, // Include the related custom risk
    },
  });
  return regles;
}
