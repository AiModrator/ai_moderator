


async function routeWrapper(fn:any){
   
        return async (req:any , res:any , next:any )=>{
            try {
                return await fn(req , res , next) ;
            } catch (error) {
                next(error)
            }
        }
   
}

export {routeWrapper}