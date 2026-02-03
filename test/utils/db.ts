import {prisma} from '../../src/config/prismaClient'




export async function clearTestDatabase() {
  // 1. Supprimer les éléments sans dépendances circulaires complexes d'abord
  await prisma.scan.deleteMany();
  await prisma.post.deleteMany(); // Dépend de Forum et User
  await prisma.forum.deleteMany(); // Dépend de Company
  await prisma.company.deleteMany(); // Dépend de User
  await prisma.user.deleteMany(); // Racine
}




/**
 * Insère un jeu de données minimal pour les tests.
 * L'ordre est inverse : du moins dépendant au plus dépendant (Top-down)
 */
export async function seedTestDatabase() {
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
      user_id: '1',
      title: "Bienvenue",
      content: "Ceci est le premier post de test",
      created_at: new Date(),
      updated_at: new Date(),
    }
  });

  return { userId: user.id, companyId: company.id, forumId: forum.id };
}