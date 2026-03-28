import { mock } from "node:test";



export function mockWebhookRequestPayload(idSource:number ){
    const contents = [
    // Très court : Pour tester les badges ou les titres
    "Statut OK.",

    // Moyen : Une phrase classique de type notification ou commentaire
    "L'utilisateur a modifié ses paramètres de profil ce matin à 10h42 depuis un terminal Linux.",

    // Paragraphe standard : Pour tester le rendu d'un post ou d'une description
    "Le déploiement continu via Docker permet d'assurer une cohérence parfaite entre l'environnement de développement sous Arch Linux et la production. En utilisant des multi-stage builds, on optimise non seulement la taille des images mais aussi la sécurité globale du pipeline.",

    // Texte long : Pour tester le scroll, le "Read More" ou les performances de Prisma/Redis
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Il est important de tester comment l'application réagit lorsqu'un utilisateur décide d'écrire un pavé énorme qui pourrait potentiellement casser la mise en page CSS ou ralentir le rendu du composant React.",

    // Technique/Code : Pour tester la gestion des caractères spéciaux ou du Markdown
    "SELECT * FROM users WHERE role = 'admin' AND created_at > '2026-01-01'; // Test d'injection ou de formatage de code."
];

    return {
        id_source: idSource,
        contents
    }
}


export const mockAxiosFactory = {
    getAxiosClient: (url: string, headers?: any, timeout: number = 1000) => ({
        getNewContent: async (url: string, lastPolledAt: string) => {
            // On crée une promesse qui attend 1s avant de résoudre avec les données
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(getMockContentForPolling());
                }, 1000);
            });
        }
    })
}

function getMockContentForPolling(){
    return  [
                    {
                        content:'contenst 1' , 
                        created_at: new Date()
                    } , 
                     {
                        content:'contenst 1' , 
                        created_at: new Date()
                    } ,
                     {
                        content:'contenst 1' , 
                        created_at: new Date()
                    } ,
                     {
                        content:'contenst 1' , 
                        created_at: new Date()
                    } ,
                   
                ]
}