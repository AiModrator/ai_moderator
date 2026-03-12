import { prisma } from "../config/prismaClient";
import { ChatChannel } from "../types/types";



 export async function upsertChatChannel(chat: ChatChannel, companyId: string) {
    const data = {
        experience_id: chat.experience_id,
        experience_name: chat.experience_name,
        ban_media: chat.ban_media,
        ban_urls: chat.ban_urls,
        who_can_post: chat.who_can_post,
        who_can_react: chat.who_can_react,
        user_posts_cooldown_seconds: chat.user_posts_cooldown_seconds,
        banned_words: chat.banned_words,
        company_id: companyId,
    };

    await prisma.chatChannel.upsert({
        where: { id: chat.id },
        update: data,
        create: { id: chat.id, ...data },
    });
}
