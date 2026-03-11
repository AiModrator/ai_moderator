import { ForumPosts } from "@whop/sdk/resources/forum-posts";
import { Post } from "src/types/types";



function tokinizer(text: string):number {
    return 0 ; 
    
}


export function classifiePosts(posts: Post[], maxTokens: number) {
    let classifiedPosts: Post[][] = [];
    let unclassifiedPosts: Post[] = []; // Pour les posts sans contenu
    let currentBatch: Post[] = [];
    let currentTokenCount = 0;

    for (const post of posts) {
        // 1. Gestion des posts vides
        if (!post.content || post.content.trim() === "") {
            unclassifiedPosts.push(post);
            continue;
        }

        const postTokens = tokinizer(post.content);

        // 2. Cas particulier : Le post seul est plus gros que maxTokens
        if (postTokens > maxTokens) {
            // On ferme le batch actuel s'il existe
            if (currentBatch.length > 0) {
                classifiedPosts.push(currentBatch);
                currentBatch = [];
                currentTokenCount = 0;
            }
            // On ajoute ce post "géant" tout seul dans son propre groupe
            classifiedPosts.push([post]);
            continue;
        }

        // 3. Logique de regroupement standard
        if (currentTokenCount + postTokens > maxTokens) {
            classifiedPosts.push(currentBatch);
            currentBatch = [post];
            currentTokenCount = postTokens;
        } else {
            currentBatch.push(post);
            currentTokenCount += postTokens;
        }
    }

    // 4. Ajout du reliquat après la boucle
    if (currentBatch.length > 0) {
        classifiedPosts.push(currentBatch);
    }

    return {
        unclassifiedPosts,
        classifiedPosts
    };
}

