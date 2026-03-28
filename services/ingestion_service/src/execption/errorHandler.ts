import { ApiError, ForbiddenError, UnauthorizedError } from "../execption/execption.js";
import { errorResponse } from "../utils/apiResponse.js";




//TODO :  Je doit normaliser   la reponse pour les requete 
export const globalErrorHandler = (error: any, req: any, res: any) => {

    if (error instanceof UnauthorizedError) {
        return errorResponse(res, error.message, error.statusCode);
    }

    if (error instanceof ForbiddenError) {
        return errorResponse(res, error.message, error.statusCode);
    }
    return errorResponse(res, error.message, 500);
};