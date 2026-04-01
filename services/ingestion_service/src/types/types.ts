// 1. Définition de l'interface pour plus de clarté
export interface ContentItem {
    content: string;
    created_at: Date;
    id: string | number ;
}




//* C'est le type du contenu inserer dans le queue du content 
export type contentQueuItem = { 
	content :string , 
	id : string  
}