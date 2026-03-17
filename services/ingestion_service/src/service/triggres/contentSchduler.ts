import { contentQueue } from "../queue/queue.js";









function tokinizer(text: string):number {
    return 0 ; 
    
}


export function classifiePosts(contents:string [] , maxTokens: number) {

    let classifiedPosts : string [][] = [] ;
    let unclassifiedPosts : string [] = []
    let tokenCount = 0 ;
    for (const content of contents) {
        let l:string [] = [] ;
        if(content){
             tokenCount += tokinizer(content );
             if(tokenCount>= maxTokens){
                l.push(content)
             }else{
                classifiedPosts.push(l) ;
                tokenCount = tokinizer(content ) ; 
                l  = [content]
             }
             
        }
        unclassifiedPosts.push(content) ;

    }
    return {
        unclassifiedPosts , 
        classifiedPosts
    }

}




export async function postScheduler(sourceId:number   ,  contents:string [] , maxTokens: number) {

    const {unclassifiedPosts , classifiedPosts} = classifiePosts(contents , maxTokens) ;
   
    for (const postList of classifiedPosts) {
        await contentQueue.add('processPost', {
            postList: postList,
            sourceId,
        });
    }
}
