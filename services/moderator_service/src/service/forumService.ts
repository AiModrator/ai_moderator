import { getAllForum, toggleModeration } from "../models/forum";
import { Forum } from "@prisma/client";

export async function listForums(): Promise<Forum[]> {
    return await getAllForum();
}

export async function toggleForumModeration(forumId: string): Promise<Forum> {
    return await toggleModeration(forumId);
}