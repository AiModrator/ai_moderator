

import prisma from '@moderator/database'




export const  getDefaultSource = async (idUser: string) => {
    const source = await prisma.source.findFirst({
        where: {
            id_user : idUser , 
            is_default : true
        }
    })
    return source
}












export  async function  getSourceById (idSource : string) {
    const source = await prisma.source.findFirst({
        where: {
            id : idSource
        }
    })
    return source
}