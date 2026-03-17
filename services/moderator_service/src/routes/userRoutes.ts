import { Request , Response, Router } from "express";   
import { prisma } from '../config/prismaClient';
import { UserData, User, Company, Forum, ChatChannel } from '../types/types';
import { upsertChatChannel } from "../models/chatChannel";
import { upsertCompany } from "../models/company";
import { upsertForum } from "../models/forum";
import { upsertUser } from "../models/user";






function synchUserData(router: Router) {
    router.post('/api/validateUser', async (req: Request, res: Response) => {

        try {
            const userData: UserData = req.body;
            console.log('userData', userData)

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

    );
}




export function setUserRoute(router: Router) {
    synchUserData(router);
}







