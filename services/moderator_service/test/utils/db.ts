import prisma, { ContentSource, User } from "@moderator/database";













export async function clearDatabase(): Promise<void> {
  console.log("🧹 Début du nettoyage complet de la base de données...");

  try {
    // On utilise une transaction pour s'assurer que tout est supprimé ou rien du tout
    await prisma.logs.deleteMany();
    await prisma.content.deleteMany();

    await prisma.apiKey.deleteMany();
    await prisma.contentSource.deleteMany();

    await prisma.user.deleteMany();
    console.log("✅ Base de données vidée avec succès.");
  } catch (error) {
    console.error("❌ Erreur lors du nettoyage de la base de données :", error);
    throw error;
  }
}




export async function checkDbConnection() {
  try {
    await prisma.$connect();
    console.log("--- DEBUG PRISMA CONFIG ---");
    console.log("DATABASE_URL d'origine :", process.env.DATABASE_URL);

    // Accéder à la configuration interne de l'instance prisma
    // @ts-ignore (pour accéder aux propriétés privées en debug)
    const datasourceUrl = prisma._engineConfig?.datasources?.[0]?.url?.value;
    console.log("URL utilisée par l'instance Prisma :", datasourceUrl);
    console.log("----------------------------");
    console.log('✅ Connexion à la base de données réussie via Prisma !');
  } catch (error) {
    console.error('❌ Impossible de se connecter à la base de données :', error);
    throw error;
  }
}



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
