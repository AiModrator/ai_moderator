import { Post, User, Forum } from '../../src/types/types';

export interface WhopClientConfig {
  postsPerCall?: number; // Nombre de posts à générer par appel
  includeVariation?: boolean; // Si true, variation dans le nombre de posts
}

/**
 * Mock du client Whop pour le polling
 */
export class MockWhopClient {
  private config: Required<WhopClientConfig>;
  private postCounter = 0;
  private mockUsers: User[];
  private mockForum: Forum;

  constructor(config: WhopClientConfig = {}) {
    this.config = {
      postsPerCall: config.postsPerCall ?? 50,
      includeVariation: config.includeVariation ?? false,
    };

    // Initialiser les données mock
    this.mockUsers = this.generateMockUsers(5);
    this.mockForum = this.generateMockForum();
  }

  /**
   * Simule la récupération de nouveaux posts
   * @param forumLastExternalPostId - ID du dernier post polling
   * @param forumExperienceId - ID de l'expérience (forum)
   * @returns Promise<Post[]> - Liste de posts mock
   */
  async getNewPosts(
    forumLastExternalPostId: string,
    forumExperienceId: string
  ): Promise<Post[]> {
    // Simuler un délai réseau
    await this.sleep(200);

    // Déterminer le nombre de posts à retourner
    const postsCount = this.config.includeVariation
      ? Math.floor(Math.random() * (this.config.postsPerCall * 1.5 - this.config.postsPerCall / 2)) + Math.floor(this.config.postsPerCall / 2)
      : this.config.postsPerCall;

    // Générer les posts
    const posts: Post[] = [];
    for (let i = 0; i < postsCount; i++) {
      posts.push(this.generateMockPost());
    }

    return posts;
  }

  /**
   * Récupérer le nombre de posts configuré
   */
  getConfiguredPostCount(): number {
    return this.config.postsPerCall;
  }

  /**
   * Reconfigurer le nombre de posts
   */
  setConfig(config: Partial<WhopClientConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Réinitialiser le compteur de posts
   */
  reset(): void {
    this.postCounter = 0;
  }

  // ============ Private Methods ============

  private generateMockPost(): Post {
    const user = this.mockUsers[Math.floor(Math.random() * this.mockUsers.length)];
    const isReply = Math.random() > 0.8;

    return {
      id: `post_${++this.postCounter}`,
      forum_id: this.mockForum.id,
      title: isReply ? null : `Post ${this.postCounter}`,
      content: this.generateMockContent(),
      created_at: new Date(Date.now() - Math.random() * 86400000), // Dans les 24h
      updated_at: new Date(),
      is_edited: Math.random() > 0.9,
      is_poster_admin: Math.random() > 0.95,
      is_pinned: Math.random() > 0.98,
      parent_id: isReply ? `post_${Math.max(1, this.postCounter - 10)}` : null,
      user_id: user.id,
      view_count: Math.floor(Math.random() * 500),
      like_count: Math.floor(Math.random() * 100),
      comment_count: Math.floor(Math.random() * 50),
      forum: this.mockForum,
      user: user,
      parent: null,
      children: [],
    };
  }

  private generateMockContent(): string {
    const contents = [
      'This is a great discussion about our platform BLOCKED_CONTENT.',
      'I have some feedback on the recent changes BLOCKED_CONTENT.',
      'Does anyone know how to solve this issue?',
      'Thank you for the update!',
      'I disagree with this approach BLOCKED_CONTENT .',
      'Can we discuss this further?',
      'This is amazing news!',
      'I think we should reconsider.',
      'Great solution, thanks for sharing.',
      'Looking forward to this feature.',
    ];
    return contents[Math.floor(Math.random() * contents.length)];
  }

  private generateMockUsers(count: number): User[] {
    const users: User[] = [];
    for (let i = 1; i <= count; i++) {
      users.push({
        id: `user_${i}`,
        username: `user${i}`,
        name: `User ${i}`,
        bio: `Bio of user ${i}`,
        profile_picture_url: null,
        created_at: new Date(),
      });
    }
    return users;
  }

  private generateMockForum(): Forum {
    return {
      id: 'forum_1',
      experience_id: 'exp_123',
      experience_name: 'Test Experience',
      company_id: 'company_1',
      who_can_post: 'members',
      who_can_comment: 'members',
      email_notification_preference: 'weekly',
    };
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
