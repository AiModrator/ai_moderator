import prisma from "@moderator/database";


export async function insertLog(phase: any, step: any, duration: number, sourceId?: number, error?: string) {
    
     const reponce  = await prisma.logs.create({
        data: {
            phase: phase,
            step:  step , 
            // source_id: sourceId,
            duration_ms: duration,
            error: error,
            created_at: new  Date()
        }

    });

}

