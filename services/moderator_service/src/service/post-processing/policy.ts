import { Forum } from "../../../../generated/browser";



export  interface Risk {
  risque: string;
  description: string;
}

interface Policy {
  risks: Risk[];
  formDescrition: string;
  formLanguage : string ;
}



export const resolveUserPolicy = async (
  forumId: string,
  getRisksForForum: (forumId: string) => Promise<any[]>  , 
  getFormById : (forumId:string) => Promise<any>
): Promise<Policy> => {

  const regles = await getRisksForForum(forumId);
  const form = await getFormById(forumId) ;

  const risks: Risk[] = [];
 

  for (const regle of regles) {
    if (regle.risque) {
      risks.push({
        risque: regle.risque.nom,
        description: regle.risque.description,
      });
    }
    if (regle.customized_risque) {
      risks.push({
        risque: regle.customized_risque.nom,
        description: regle.customized_risque.description,
      });
    }
  }

  return {
    risks,
    formDescrition : form.forumDescription, 
    formLanguage : form.forumLanguage 
  };
};
