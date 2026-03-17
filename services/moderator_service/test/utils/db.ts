import { PrismaClient } from '@prisma/client'

export async function clearTestDatabase(prisma: PrismaClient) {
  // 1. Supprimer les éléments sans dépendances circulaires complexes d'abord
  await prisma.post.deleteMany(); // Dépend de Forum et User
  await prisma.forum.deleteMany(); // Dépend de Company
  await prisma.company.deleteMany(); // Dépend de User
  await prisma.user.deleteMany(); // Racine
  await prisma.$disconnect();
}




/**
 * Insère un jeu de données minimal pour les tests.
 * L'ordre est inverse : du moins dépendant au plus dépendant (Top-down)
 */
export async function seedTestDatabase(prisma: PrismaClient) {
  // 1. Créer un Utilisateur
  const user = await prisma.user.create({
    data: {
      id: "user-1",
      username: "john_doe",
      name: "John Doe",
      created_at: new Date(),
    }
  });

  // 2. Créer une Entreprise
  const company = await prisma.company.create({
    data: {
      id: "comp-1",
      title: "Tech Corp",
      user_id: user.id,
      created_at: new Date(),
      updated_at: new Date(),
    }
  });

  // 3. Créer un Forum
  const forum = await prisma.forum.create({
    data: {
      id: "forum-1",
      experience_id: "exp-123",
      experience_name: "General Discussion",
      company_id: company.id,
    }
  });

  // 4. Créer un Post
  await prisma.post.create({
    data: {
      id: "post-1",
      forum_id: forum.id,
      user_id: user.id,
      title: "Bienvenue",
      content: "Ceci est le premier post de test",
      created_at: new Date(),
      updated_at: new Date(),
    }
  });

  return { userId: user.id, companyId: company.id, forumId: forum.id };
}

export async function seedForums(prisma: PrismaClient) {
    const user = await prisma.user.create({
        data: {
          id: "user-2",
          username: "jane_doe",
          name: "Jane Doe",
          created_at: new Date(),
        }
      });
    
      const company = await prisma.company.create({
        data: {
          id: "comp-2",
          title: "Creative Inc.",
          user_id: user.id,
          created_at: new Date(),
          updated_at: new Date(),
        }
      });

    await prisma.forum.createMany({
      data: [
        {
          id: "forum-3",
          experience_id: "exp-321",
          experience_name: "General Discussion",
          company_id: company.id,
        },
        {
          id: "forum-4",
          experience_id: "exp-654",
          experience_name: "Support",
          company_id: company.id,
        },
      ],
    });
  }