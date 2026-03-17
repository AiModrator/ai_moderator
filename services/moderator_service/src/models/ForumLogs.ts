import { prisma } from "../config/prismaClient";



export type formState =  "POLLING_STARTED" | "POLLING_SUCCESS" | "POLLING_FAILED" | "PROCESSING_SPAM" | "PROCESSING_TRANSLATION" | "PROCESSING_CONTENT" | "PROCESSING_AI_CALL" ;

export interface CreateForumLogInput {
  forumId: string
  state:formState
  isRetry: boolean;
  durationMs: number;
  error?: string;
}

/**
 * Creates a new forum log entry for tracking forum polling/processing activity.
 * 
 * @param input - Log data to create
 * @returns Created ForumLogs record
 * @throws Error if forum doesn't exist or database error occurs
 */
export const createForumLog = async (input: CreateForumLogInput) => {
  try {
    const forumLog = await prisma.forumLogs.create({
      data: {
        forum_id: input.forumId,
        state: input.state,
        isRetry: input.isRetry,
        duration_ms: input.durationMs,
        error: input.error || null,
      },
      include: {
        forum: true,
      },
    });

    return forumLog;
  } catch (error) {
    console.error("Error creating forum log:", error);
    throw error;
  }
};

/**
 * Retrieves all logs for a specific forum.
 * 
 * @param forumId - Forum ID to filter by
 * @param limit - Maximum number of logs to return (default: 100)
 * @returns Array of ForumLogs records
 */
export const getForumLogs = async (forumId: string, limit: number = 100) => {
  return prisma.forumLogs.findMany({
    where: { forum_id: forumId },
    orderBy: { created_at: "desc" },
    take: limit,
  });
};

/**
 * Retrieves failed logs for monitoring/alerting purposes.
 * 
 * @param forumId - Optional forum ID filter
 * @returns Array of failed ForumLogs records
 */
export const getFailedLogs = async (forumId?: string) => {
  return prisma.forumLogs.findMany({
    where: {
      ...(forumId && { forum_id: forumId }),
      state: "POLLING_FAILED",
    },
    orderBy: { created_at: "desc" },
  });
};
