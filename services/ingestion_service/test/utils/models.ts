import prisma , {  ApiKey, ContentSource, User } from "@moderator/database"
import { hashApiKey  , generateSecureApiKey} from "../../src/utils/hash";

/**
 * Crée un utilisateur de test et retourne son ID
 */
export async function createTestUser(data?: { email?: string; name?: string; }): Promise<User> {
  console.log("   -> Entrée dans createTestUser");
  
  try {
      const user = await prisma.user.create({
        data: {
          email: data?.email || `test-${Date.now()}@example.com`,
          name: data?.name || "Test User",
        },
      });
      console.log("   -> Utilisateur créé avec succès dans Prisma");
      return user;
  } catch (error) {
      console.error("   -> ERREUR PRISMA DANS createTestUser :", error);
      throw error;
  }
}

/**
 * Crée une ApiKey de test associée à un utilisateur et retourne son ID
 */
export async function createTestApiKey(userId: number, disabled: boolean = false): Promise<string> {
  const apiKey = generateSecureApiKey();
  const apikeyHashed = hashApiKey(apiKey) 
  console.log("   -> apikeyHashed" , apikeyHashed)

   await prisma.apiKey.create({
    data: {
      key: apikeyHashed,
      disabled,
      user_id: userId,
    },
  });
  return apiKey;
}

/**
 * Crée une ContentSource de test associée à un utilisateur et retourne son ID
 */
export async function createTestContentSource(userId: number, data?: {
  url?: string;
  forumDescription?: string;
  forumLanguage?: string;
  is_default?: boolean;
}): Promise<ContentSource> {
  const contentSource = await prisma.contentSource.create({
    data: {
      url: data?.url || "https://example.com/forum",
      forumDescription: data?.forumDescription || "Test Forum",
      forumLanguage: data?.forumLanguage || "en",
      is_default: data?.is_default ?? false,
      id_user: userId,
    },
  });
  return contentSource;
}

/**
 * Cleanup : supprime un utilisateur et toutes ses données associées
 */
export async function deleteTestUser(userId: number): Promise<void> {
  await prisma.user.delete({
    where: { id: userId },
  });
}

/**
 * Cleanup : supprime une ContentSource
 */
export async function deleteTestContentSource(sourceId: number): Promise<void> {
  await prisma.contentSource.delete({
    where: { id: sourceId },
  });
}

// Cleanup  

/**
 * Supprime toutes les données de la base de données.
 * L'ordre est crucial pour respecter les contraintes d'intégrité (FK).
 */
export async function clearDatabase(): Promise<void> {
  console.log("🧹 Début du nettoyage complet de la base de données...");

  try {
    // On utilise une transaction pour s'assurer que tout est supprimé ou rien du tout
    await prisma.$transaction([
      // 1. Supprimer les enfants d'abord (ceux qui dépendent des autres)
      prisma.logs.deleteMany(),
      prisma.content.deleteMany(),
      
      // 2. Supprimer les parents intermédiaires
      prisma.apiKey.deleteMany(),
      prisma.contentSource.deleteMany(),
      
      // 3. Supprimer les parents racines (User)
      prisma.user.deleteMany(),
    ]);

    console.log("✅ Base de données vidée avec succès.");
  } catch (error) {
    console.error("❌ Erreur lors du nettoyage de la base de données :", error);
    throw error;
  }
}

/**
 * Fonction spécifique pour supprimer uniquement les logs (utile pour le debug)
 */
export async function clearLogs(): Promise<void> {
    await prisma.logs.deleteMany();
    console.log("📑 Logs supprimés.");
}