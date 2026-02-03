
import Whop from "@whop/sdk";
import { ForumPostListResponsesCursorPage } from "@whop/sdk/resources/forum-posts";

const client = new Whop({
  apiKey: process.env.WHOP_API_KEY,
});



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