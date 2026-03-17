import { Forum } from "../../../generated/browser";
import { prisma } from "../config/prismaClient";
import {  } from "@prisma/client";





export async function getAllForum():Promise<{ id: string; experience_id: string | null; experience_name: string | null; company_id: string; who_can_post: string | null; who_can_comment: string | null; email_notification_preference: string | null; }[]> {
    const forums = await prisma.forum.findMany();
    if(!forums){
        throw new Error("Aucune forum existe ")
    }
    return forums ;
}




export async function upsertForum(forum: Forum, companyId: string) {
    const data = {
        experience_id: forum.experience_id,
        experience_name: forum.experience_name,
        company_id: companyId,
        who_can_post: forum.who_can_post,
        who_can_comment: forum.who_can_comment,
        email_notification_preference: forum.email_notification_preference,
    };

    await prisma.forum.upsert({
        where: { id: forum.id },
        update: data,
        create: { id: forum.id, ...data },
    });
}


export async function toggleModeration(forumId: string): Promise<Forum> {
    const forum = await prisma.forum.findUnique({
        where: { id: forumId },
    });

    if (!forum) {
        throw new Error("Forum not found");
    }

    const updatedForum = await prisma.forum.update({
        where: { id: forumId },
        data: { is_moderated: !forum.is_moderated },
    });

    return updatedForum;
}

export async function updateForumAfterPolling(forumId: string, lastExternalPostId: string | null) {
    return prisma.forum.update({
        where: { id: forumId },
        data: {
            last_polled_at: new Date(),
            last_external_post_id: lastExternalPostId,
            polling_failed: false,
            last_polling_error: null,
        },
    });
}



export async function updateForumOnPollingFailure(forumId: string, error: any) {
    return prisma.forum.update({
        where: { id: forumId },
        data: {
            polling_failed: true,
            last_polling_error: error.message || 'Unknown error',
        },
    });
}



export const getForumsToPoll = async (bashSize: number) => {
    return prisma.forum.findMany({
        where: {
            polling_failed: false,
        },
        orderBy: {
            last_polled_at: 'asc',
        },
        take: bashSize,
    });
};




export const getFormByIdExperience = async (idForum:string)=>{

    return prisma.forum.findUnique({
        where: {
            experience_id:idForum  
        }
    })
} 