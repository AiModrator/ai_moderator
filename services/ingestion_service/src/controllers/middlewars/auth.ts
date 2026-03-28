
import { UnauthorizedError } from "../../execption/execption.js"
import { getApiKeyByKey  , getUserFromApiKey} from "../../models/apiKey.js"
import { hashApiKey } from "../../utils/hash.js"




export const validateApiKey = async (req: any, res: any, next: any) => {
    try {
        const header = req.headers['authorization']
        console.log(header)
        console.log('c est l key hash '  , hashApiKey(header))
    // const apiKey =  header.split(' ')[1]
    const hashedApiKey =   hashApiKey(header)
    
    
    if(!header){
        throw new UnauthorizedError ('Unauthorized')
    }
    const apiKeyDb = await getApiKeyByKey(hashedApiKey)

    if (!apiKeyDb) {
        throw new UnauthorizedError ('Unauthorized')
    }
    

    req.user = await getUserFromApiKey(apiKeyDb.key)

    if (!req.user) {
        throw new UnauthorizedError ('Unauthorized')
    }
    } catch (error) {
        throw new UnauthorizedError ('Unauthorized')
    }
    
    

    next()
}







