import { getDefaultSource, getSourceById } from "src/models/content.js";





function validateData(req: any, res: any, next: any) {
    const data = req.body;

    if (!data && data.contents && data.contents.length === 0) {
        return res.status(400).json({ error: 'Donnees manquantes' });
    }
    
    next();
}

async function getSource(req: any, res: any, next: any) {

    const idSource = req.body.data.id_source;
    let  source ; 
    if (idSource) {
        source = await getSourceById(idSource);
    }else{
        source = await getDefaultSource(req.user.id);
    }

    if(!source){
        return res.status(400).json({ error: 'Source introuvable' });
    } 
    req.ContentSource = source ; 
    next();
}


