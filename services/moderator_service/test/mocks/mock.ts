import { ContentQueueData } from "../../src/types/types";




export function getContentQueue(idSource : number) : ContentQueueData{

    return {
        contents:[
            {
                id : 1,
                content : "test content",
               
            }, 
              {
                id : 2,
                content : "test content",
               
            }, 
              {
                id : 3,
                content : "test content",
               
            }, 
              {
                id : 4,
                content : "test content",
               
            }, 
        ],
        sourceId : idSource
    }
    
}