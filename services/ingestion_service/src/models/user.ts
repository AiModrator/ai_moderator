
import prisma from '@moderator/database'





const getUserByApiKey = async (apiKey : string) => {
    const user = await prisma.user.findFirst({
        where: {
            apiKey : apiKey
        }
    })
    return user
}



export const getUserToPoll = async (bashSize: number) => {
    return prisma.user.findMany({
        where: {
            polling_failed: false,
        },
        orderBy: {
            last_polled_at: 'asc',
        },
        take: bashSize,
    });
};




export async function updateUserWithNoContent(userId : string) {
    return prisma.user.update({
        where: { id: userId },
        data: {
            last_polled_at: new Date(),
            polling_failed: false,
            last_polling_error: null,
        },
    });
}



export async function updateForumOnPollingFailure(userId: string, error: any) {
    return prisma.user.update({
        where: { id: userId },
        data: {
            polling_failed: true,
            last_polling_error: error.message || 'Unknown error',
        },
    
    });
}

export async function updateUserAfterPolling(userId: number) {
    return prisma.user.update({
        where: { id: userId },
        data: {
          last_polled_at: new Date(),
            polling_failed: false,
            last_polling_error: null,
        },
    });
}





