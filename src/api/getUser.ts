import { Request , Response } from "express";   
import { prisma } from '../presistence/prismaClient';
import { UserData, User, Company, Forum, ChatChannel } from '../types/types';



async function upsertUser(user: User): Promise<boolean> {
    const existingUser = await prisma.user.findUnique({
        where: { id: user.id },
    });

    if (existingUser) {
        await prisma.user.update({
            where: { id: user.id },
            data: {
                username: user.username,
                name: user.name,
                bio: user.bio,
                profile_picture_url: user.profile_picture_url,
            },
        });
        return false;
    } else {
        await prisma.user.create({
            data: {
                id: user.id,
                username: user.username,
                name: user.name,
                bio: user.bio,
                profile_picture_url: user.profile_picture_url,
                created_at: new Date(user.created_at),
            },
        });
        return true;
    }
}

async function upsertCompany(company: Company, userId: string) {
    const existingCompany = await prisma.company.findUnique({
        where: { id: company.id },
    });

    const data = {
        title: company.title,
        description: company.description,
        verified: company.verified,
        business_type: company.business_type,
        industry_type: company.industry_type,
        send_customer_emails: company.send_customer_emails,
        updated_at: new Date(company.updated_at),
        member_count: company.member_count,
        route: company.route,
        logo_url: company.logo_url,
        user_id: userId,
    };

    if (existingCompany) {
        await prisma.company.update({
            where: { id: company.id },
            data: data,
        });
    } else {
        await prisma.company.create({
            data: {
                id: company.id,
                created_at: new Date(company.created_at),
                ...data
            },
        });
    }
}

async function upsertForum(forum: Forum, companyId: string) {
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

async function upsertChatChannel(chat: ChatChannel, companyId: string) {
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


export async function validateUser(req: Request, res: Response) {
    
    try {
        const userData: UserData = req.body;
        console.log('userData',userData)

        const { user, company, forums, chats } = userData;


        const isNewUser = await upsertUser(user);
        await upsertCompany(company, user.id);

        if (forums && forums.length > 0) {
            await Promise.all(forums.map(forum => upsertForum(forum, company.id)));
        }

        if (chats && chats.length > 0) {
            await Promise.all(chats.map(chat => upsertChatChannel(chat, company.id)));
        }

        if (isNewUser) {
            return res.status(201).json({ message: 'User created' });
        } else {
            return res.status(200).json({ message: 'User validated' });
        }
    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: 'Internal Server Error' });
    }
}
