import { beforeAll } from 'vitest'
import { clearContentQueue, createTestApiKey, createTestContentSource, createTestUser } from './index.js'
import prisma, { ApiKey, User, ContentSource } from '@ai-moderator/database';
import { clearDatabase } from './models.js';
import { mock } from 'node:test';
import { get } from 'node:http';
import { mockAxiosFactory } from './mock.js';
import { clearAllQueues } from './queue.js';


export function setupWebHooksTest() {
    // On garde l'objet de référence
    const context = {
        user: {} as User, 
        apiKey: ''  , 
        contentSource: {} as ContentSource
    }

    beforeAll(async () => {
        console.log("🚀 Setup WebHook environment START");
        
        try {
            // 1. ATTENDRE la connexion
            await checkDbConnection(); 

            // 2. SUPPRIMER la base de données
            await clearDatabase();

            // 3. VIDER la queue
            await clearContentQueue();

            // 4. ATTENDRE les créations successives
            console.log("Creating user...");
            context.user = await createTestUser();
            
            console.log("Creating API Key...");
            context.apiKey = await createTestApiKey(context.user.id);
            
            console.log("Creating Content Source...");
            context.contentSource = await createTestContentSource(context.user.id);
            
            console.log("✅ Setup WebHook environment COMPLETE");
        } catch (err) {
            console.error("❌ Critical error during setup:", err);
            throw err; // Permet d'arrêter le test proprement au lieu de timeout
        }
    }, 20000); // On donne 20s au cas où la DB est lente

    // IMPORTANT : On retourne l'objet lui-même, pas une déstructuration {...context}
    return context;
}


export function setupPollingTest(){
     const context = {
        user: {} as User, 
        apiKey: ''  , 
        contentSource: {} as ContentSource , 
        mockAxiosClient: mockAxiosFactory 
    }

    beforeAll(async () => {
          console.log("🚀 Setup polling environment START");
        
        try {
            // 1. ATTENDRE la connexion
            await checkDbConnection(); 

            // 2. SUPPRIMER la base de données
            await clearDatabase();

            // 3. VIDER la queue
            await clearAllQueues();

            // 4. ATTENDRE les créations successives
            console.log("Creating user...");
            context.user = await createTestUser();
            
            console.log("Creating API Key...");
            context.apiKey = await createTestApiKey(context.user.id);
            
            console.log("Creating Content Source...");
            context.contentSource = await createTestContentSource(context.user.id);
            
            console.log("✅ Setup WebHook environment COMPLETE");
        } catch (err) {
            console.error("❌ Critical error during setup:", err);
            throw err; // Permet d'arrêter le test proprement au lieu de timeout
        }
    }, 20000); // On donne 20s au cas où la DB est lente

    // IMPORTANT : On retourne l'objet lui-même, pas une déstructuration {...context}
    return context;

    }


    





async function checkDbConnection() {
  try {
    await prisma.$connect();
    console.log('✅ Connexion à la base de données réussie via Prisma !');
  } catch (error) {
    console.error('❌ Impossible de se connecter à la base de données :', error);
    throw error;
  }
}




