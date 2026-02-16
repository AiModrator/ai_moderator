import { ForumPosts } from "@whop/sdk/resources/forum-posts";
import { Post } from "../types/types";



function tokinizer(text: string):number {
    return 0 ; 
    
}


export function classifiePosts(posts:Post [] , maxTokens: number) {
    let classifiedPosts : Post [][] = [] ;
    let unclassifiedPosts : Post [] = []
    let tokenCount = 0 ;
    for (const post of posts) {
        let l:Post [] = [] ;
        if(post.content){
             tokenCount += tokinizer(post.content );
             if(tokenCount>= maxTokens){
                l.push(post)
             }else{
                classifiedPosts.push(l) ;
                tokenCount = tokinizer(post.content ) ; 
                l  = [post]
             }
             
        }
        unclassifiedPosts.push(post) ;

    }
    return {
        unclassifiedPosts , 
        classifiedPosts
    }

}