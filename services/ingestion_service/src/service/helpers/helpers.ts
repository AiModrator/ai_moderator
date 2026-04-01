
import { ContentItem } from "src/types/types.js";
import { updateContentPollingFailure, updateSourceAfterPolling } from "../../models/contentSource.js";
import { contentScheduler } from "../triggres/schdulers.js";




export async function processNewPosts(
    newContent: any[],
    idSource: number
) {

    //TODO je doit presister unclassifiedPost dans la base de donne

    const maxToken = 20 
    await contentScheduler(idSource, newContent, maxToken);
    const mostRecentContentDate = getMostRecentDate(newContent);
    await updateSourceAfterPolling(idSource , mostRecentContentDate) ;

}





 function getMostRecentDate(contents: any[]): Date  {
  
    // On transforme les dates en nombres (timestamps) pour trouver le maximum
    const mostRecentTimestamp = Math.max(
        ...contents.map(item => new Date(item.created_at).getTime())
    );

    return new Date(mostRecentTimestamp);
}


function tokinizer(text: string):number {
    return 10 ; 
    
}







export function chunking(contents: ContentItem[], maxTokens: number) {
    let classifiedPosts: ContentItem[][] = []; // Tableau de groupes d'objets
    let currentGroup: ContentItem[] = []; 
    let currentTokens = 0;

    for (const item of contents) {
        // Sécurité : on vérifie que l'objet et sa propriété content existent
        if (!item || !item.content) continue;

        // On calcule les tokens sur la chaîne de texte uniquement
        const tokens = tokinizer(item.content);

        // Si l'ajout de cet objet dépasse la limite
        if (currentTokens + tokens > maxTokens && currentGroup.length > 0) {
            classifiedPosts.push(currentGroup);
            currentGroup = []; 
            currentTokens = 0;
        }

        // On ajoute l'objet ENTIER (pas juste le texte) au groupe
        currentGroup.push(item);
        currentTokens += tokens;
    }

    // On ajoute le reliquat
    if (currentGroup.length > 0) {
        classifiedPosts.push(currentGroup);
    }

    return classifiedPosts
    
}






export async function handlePollingError(sourceId: number, error: string) {
   
    await updateContentPollingFailure(sourceId, error);
    throw error; // Re-throw to trigger BullMQ's retry mechanism
}

