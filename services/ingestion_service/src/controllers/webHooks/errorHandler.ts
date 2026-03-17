import { ApiError, ForbiddenError, UnauthorizedError } from "src/execption/execption.js";




//TODO :  Je doit normaliser   la reponse pour les requete 
const globalErrorHandler =  (error: any, req: any, res: any) => {

        if(error instanceof UnauthorizedError){
            return res.status(error.statusCode).json({ error: error.message });
        }

        if(error instanceof  ForbiddenError){
            return res.status(error.statusCode).json({ error: error.message });
        }
        return res.status(500).json({ error: 'Internal server error' });
};