
import { checkDbConnection } from "@moderator/database/prismaClient";

import { clearDatabase, createTestContentSource, createTestUser } from "../utils/db";
import { addContentJobs, clearAllQueues } from "../utils/redis";

import prisma, { ContentSource, User } from "@moderator/database";
import { ContentQueueData } from "../../src/types/types";
import { getContentQueue } from "../mocks/mock";








export function setupMainTest(){
    

   let context  = {
    user: {}  as User,
    contentSource: {} as ContentSource, 
    data  : {} as ContentQueueData
   }  ;  
   beforeEach(async ()=>{

    try{
        checkDbConnection();
        clearDatabase();
        clearAllQueues() ;


        context.user = await createTestUser();
            
           
        console.log("Creating Content Source...");
        context.contentSource = await createTestContentSource(context.user.id);

        context.data = getContentQueue( context.contentSource.id);

        
       
        
    } catch (error) {
        throw error;
    }
    })
    return context;
}





