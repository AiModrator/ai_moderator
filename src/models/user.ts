import { prisma } from "../config/prismaClient";
import { User } from "../types/types";



export async function upsertUser(user: User): Promise<boolean> {
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




