
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
    await updateSourceAfterPolling(idSource);

}


function tokinizer(text: string):number {
    return 10 ; 
    
}




export function chunking(contents: string[], maxTokens: number) {
    let classifiedPosts: string[][] = [];
    let currentGroup: string[] = []; // On garde le groupe en cours en dehors de la boucle
    let currentTokens = 0;

    for (const content of contents) {
        if (!content) continue;

        const tokens = tokinizer(content);

        // Si l'ajout du post dépasse la limite, on ferme le groupe actuel
        if (currentTokens + tokens > maxTokens && currentGroup.length > 0) {
            classifiedPosts.push(currentGroup);
            currentGroup = []; // On recommence un nouveau groupe
            currentTokens = 0;
        }

        // On ajoute le contenu au groupe actuel
        currentGroup.push(content);
        currentTokens += tokens;
    }

    // Très important : On n'oublie pas d'ajouter le dernier groupe s'il n'est pas vide
    if (currentGroup.length > 0) {
        classifiedPosts.push(currentGroup);
    }

    return classifiedPosts
    
}


export function chunkingForPolling(contents: ContentItem[], maxTokens: number) {
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

