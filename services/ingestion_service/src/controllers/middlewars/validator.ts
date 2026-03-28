
import { getDefaultSource, getSourceById } from "src/models/contentSource.js";
import { errorResponse } from "../../utils/apiResponse.js";





export function validateData(req: any, res: any, next: any) {
    const payload = req.body.data; // On regarde à l'intérieur de .data

    if (!payload || !payload.contents || !Array.isArray(payload.contents) || payload.contents.length === 0) {
        return errorResponse(res, 'Données manquantes ou format de contenu invalide', 400);
    }
    next();
}


export async function getSource(req: any, res: any, next: any) {

    const idSource = req.body.data.id_source;
    let  source ; 
    if (idSource) {
        source = await getSourceById(idSource);
    }else{
        source = await getDefaultSource(req.user.id);
    }

    if(!source){
        return errorResponse(res, 'Source introuvable', 400);
    } 
    req.ContentSource = source ; 
    next();
}


