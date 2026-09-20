import prisma from "@ai-moderator/database";










export const  getDefaultSource = async (idUser: number) => {
    const source = await prisma.contentSource.findFirst({
        where: {
            id_user : idUser , 
            is_default : true
        }
    })
    return source
}





export const getContentSourceToPoll = async (bashSize: number) => {
    return prisma.contentSource.findMany({
        where: {
            polling_failed: false, 
            url : {not : null}
        },
        orderBy: {
            last_polled_at: 'asc',
        },
        take: bashSize,
    });
};





export async function updateSourceAfterPolling(contentSourceId : number , last_polled_at : Date) {
    return prisma.contentSource.update({
        where: { id: contentSourceId },
        data: {
            last_polled_at: last_polled_at,
            polling_failed: false,
            
        },
    });
}



export async function updateContentPollingFailure(contentSourceId : number , last_polling_error : string) {
    return prisma.contentSource.update({
        where: { id: contentSourceId },
        data: {
            last_polled_at: new Date(),
            polling_failed: true,
            last_polling_error : last_polling_error
            
        },
    });
}



export  async function  getSourceById (idSource : number) {
    const source = await prisma.contentSource.findFirst({
        where: {
            id : idSource
        }
    })
    return source
}




export async function updateForumOnPollingFailure(userId: number, error: any) {
    return prisma.contentSource.update({
        where: { id: userId },
        data: {
            polling_failed: true,
            last_polling_error: error.message || 'Unknown error',
        },
    
    });
}
