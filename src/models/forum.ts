import { Forum } from "../../generated/browser";
import { prisma } from "../config/prismaClient";





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
