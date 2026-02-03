import { Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { User, Company, Forum, Chat } from '../types/types';

const prisma = new PrismaClient();

interface SyncDataRequestBody {
  user: User;
  company: Company;
  forums: Forum[];
  chats: Chat[];
}

export const syncData = async (req: Request, res: Response) => {
  const { user, company, forums, chats } = req.body as SyncDataRequestBody;

  try {
    const existingUser = await prisma.user.findUnique({
      where: { id: user.id },
    });

    if (!existingUser) {
      await prisma.user.create({
        data: {
          id: user.id,
          username: user.username,
          name: user.name,
          createdAt: new Date(user.created_at),
          bio: user.bio,
          profilePictureUrl: user.profile_picture.url,
        },
      });
      return res.status(201).json({ message: 'User created successfully' });
    }

    return res.status(200).json({ message: 'User already exists' });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ message: 'Internal server error' });
  }
};
