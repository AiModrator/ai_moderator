import { Phase, Steps } from "@moderator/database/generated";
import { insertLog } from "../models/logs";


 function errorWrapper(fn:any){
   
        return async (req:any , res:any , next:any )=>{
            try {
                return await fn(req , res , next) ;
            } catch (error) {
                next(error)
            }
        }
   
}




export  function logsWrapperFactory(step : Steps , phase : Phase , sourceId?: number  ){

    
    
    return function (fnOrginal:Function){
        return async function(...args:any){
           try{     
        
           
            const debut = performance.now();
            const response = await fnOrginal(...args)
            const fin = performance.now()
            await insertLog(phase , step , fin - debut , sourceId)
              return response  ;

           }catch(err : any ){

            await insertLog(phase , step , 0 , undefined , err.message)
            throw err
           }
    }
}  }




export {errorWrapper}



