import { head } from "node_modules/axios/index.cjs"
import { UnauthorizedError } from "src/execption/execption.js"
import { getApiKeyByKey  , getUserFromApiKey} from "src/models/apiKey.js"
import { hashApiKey } from "src/utils/hash.js"




export const validateApiKey = async (req: any, res: any, next: any) => {
    const header = req.headers['authorization']

    const apiKey =  header.split(' ')[1]
    const hashedApiKey =   hashApiKey(apiKey)
    
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
    

    next()
}







