
import Whop from "@whop/sdk";
import { ForumPostListResponsesCursorPage } from "@whop/sdk/resources/forum-posts";
import { clientWhop } from "./WhopConfig";




export async function  getPostPerIdForum(id:string , client:Whop ):Promise<Whop.ForumPosts.ForumPostListResponsesCursorPage>{


  const configQuery =  {
    experience_id: id,
    first: 10,
  } 


   const page = await client.forumPosts.list(
    configQuery
   );
   
   console.log('C est la page', page)

   return page ; 

}


export async function getNewPost(last_processed_post_id: string, forumExperienceId: string) {

  const allPosts = [];
  for await (const post of clientWhop.forumPosts.list({
    experience_id: forumExperienceId,
    first : 10 
  })) {
    if (post.id == last_processed_post_id) {
      break;
    }
    allPosts.push(post);
  }
  console.log(`Total: ${allPosts.length} posts`);

  return allPosts;

}






