import prisma from '@ai-moderator/database'
import { User } from '@ai-moderator/database'


export const getApiKeyByKey = async (key : string) => {
    const apiKey = await prisma.apiKey.findFirst({
        where: {
            key : key
        }
    })
    return apiKey
}



export async function getUserFromApiKey(key: string): Promise<User | null> {

  const apiKey = await prisma.apiKey.findUnique({
    where: { key },
  });

  if (!apiKey) {
    return null;
  }

  const user = await prisma.user.findUnique({
    where: { id: apiKey.user_id },
  });

  return user;
}



