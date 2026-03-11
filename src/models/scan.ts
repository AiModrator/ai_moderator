import { prisma } from "../config/prismaClient";



export async function getLastScan ():Promise<{ id: string; last_scan_at: Date; }> {
    const lastScan = await  prisma.scan.findFirst({
        orderBy:{
            last_scan_at:'desc'
        }
    })    

    if(!lastScan){
        throw new Error("Il n'existe aucune scan")
    }

    return lastScan ; 



}


