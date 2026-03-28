
import { insertLog } from "../models/logs.js";



 function errorWrapper(fn:any){
   
        return async (req:any , res:any , next:any )=>{
            try {
                return await fn(req , res , next) ;
            } catch (error) {
                next(error)
            }
        }
   
}




export  function logsWrapperFactory(step : any , phase : any   ){

    
    
    return function (fnOrginal:Function){
        return async function(...args:any){
           try{     
        
           
            const debut = performance.now();
            const response = await fnOrginal(...args)
            const fin = performance.now()
            console.log('Temps de traitement ---->>>>>>' , fin - debut)
            await insertLog(phase , step , fin - debut)
              return response  ;

           }catch(err : any ){

            await insertLog(phase , step , 0 , undefined , err.message)
            throw err
           }
    }
}  }




export {errorWrapper}



