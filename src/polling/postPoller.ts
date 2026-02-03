import { ForumPostListResponse } from "@whop/sdk/resources/forum-posts";
import { getAllForum } from "../presistence/forum";
import { getLastScan } from "../presistence/scan";
import { getPostPerIdForum } from "../whopClient/contentRetriver";






async function getPost(){

    const last_scan_at = await getLastScan() ;
    const forums = await getAllForum() ;
    let posts:ForumPostListResponse[] = []

    forums.forEach(async(fr)=>{
    
        let dirtyPost = await getPostPerIdForum(fr.company_id)
        
        while(true){
            let tempPost:ForumPostListResponse[] = []
            dirtyPost.data.forEach(async(post)=>{
                let updated_at = new Date(post.updated_at)
                if(updated_at>last_scan_at.last_scan_at){
                    tempPost.push(post) ;
                }
                
            })
             if(tempPost.length == 0 ){
                    break ;
                }
                posts.concat(tempPost) ;
                dirtyPost  = await  dirtyPost.getNextPage() ;
        }
    })
    return posts ;

}


function sort(
  posts: ForumPostListResponse[],
  maxPostNbr: number,
  maxContent: number
): ForumPostListResponse[][] {
  const result: ForumPostListResponse[][] = [];

  let currentBatch: ForumPostListResponse[] = [];
  let currentCharCount = 0;

  for (const post of posts) {
    const postLength = post.content?.length || 0;

    // Si ajouter ce post dépasse une des contraintes
    const exceedPostLimit = currentBatch.length + 1 > maxPostNbr;
    const exceedCharLimit = currentCharCount + postLength > maxContent;

    if (exceedPostLimit || exceedCharLimit) {
      // On ferme le batch courant
      if (currentBatch.length > 0) {
        result.push(currentBatch);
      }

      // On démarre un nouveau batch
      currentBatch = [];
      currentCharCount = 0;
    }

    // Cas limite : un post seul dépasse maxContent
    if (postLength > maxContent) {
      // stratégie simple : on l’isole dans son propre batch
      result.push([post]);
      continue;
    }

    // On ajoute le post au batch courant
    currentBatch.push(post);
    currentCharCount += postLength;
  }

  // Ajouter le dernier batch s’il n’est pas vide
  if (currentBatch.length > 0) {
    result.push(currentBatch);
  }

  return result;
}



async function postPoller(){
    const posts =  await getPost();
    const soterPostsList = sort(posts , 5, 1000)
}



