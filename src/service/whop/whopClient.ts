import { getNewPost } from "./contentRetriver"


const whopClient = {
    getNewPost: async (last_processed_post_id: string, forumExperienceId: string) => 
        await getNewPost(last_processed_post_id, forumExperienceId)

}



export default whopClient 
