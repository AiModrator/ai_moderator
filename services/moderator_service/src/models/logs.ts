import prisma from "@moderator/database";
import { Phase, Steps } from "@moderator/database/generated";


export async function insertLog(phase: Phase, step: Steps ,  duration: number, sourceId?: number, error?: string) {
    
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

