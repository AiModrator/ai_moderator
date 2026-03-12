import { User, Company, Forum, Post, ChatChannel } from '../src/types/types';

/**
 * Génère des utilisateurs mock
 */
export const createMockUsers = (count: number = 5): User[] => {
  const users: User[] = [];
  for (let i = 1; i <= count; i++) {
    users.push({
      id: `user_${i}`,
      username: `user${i}`,
      name: `User ${i}`,
      bio: `Bio of user ${i}`,
      profile_picture_url: `https://example.com/avatar${i}.jpg`,
      created_at: new Date(Date.now() - i * 86400000),
    });
  }
  return users;
};

/**
 * Génère une entreprise mock
 */
export const createMockCompany = (userId: string = 'user_1'): Company => ({
  id: 'company_1',
  title: 'Test Company',
  description: 'A test company for integration testing',
  verified: true,
  business_type: 'Technology',
  industry_type: 'Software',
  send_customer_emails: true,
  created_at: new Date(),
  updated_at: new Date(),
  member_count: 150,
  route: '/test-company',
  logo_url: 'https://example.com/logo.png',
  user_id: userId,
});

/**
 * Génère un forum mock
 */
export const createMockForum = (companyId: string = 'company_1'): Forum => ({
  id: 'forum_1',
  experience_id: 'exp_123',
  experience_name: 'Test Forum',
  company_id: companyId,
  who_can_post: 'members',
  who_can_comment: 'members',
  email_notification_preference: 'weekly',
});

/**
 * Génère un post mock
 */
export const createMockPost = (
  forumId: string = 'forum_1',
  userId: string = 'user_1',
  index: number = 1
): Post => ({
  id: `post_${index}`,
  forum_id: forumId,
  title: `Post Title ${index}`,
  content: `This is the content of post ${index}`,
  created_at: new Date(Date.now() - index * 3600000),
  updated_at: new Date(),
  is_edited: false,
  is_poster_admin: false,
  is_pinned: false,
  parent_id: null,
  user_id: userId,
  view_count: Math.floor(Math.random() * 500),
  like_count: Math.floor(Math.random() * 100),
  comment_count: Math.floor(Math.random() * 50),
});

/**
 * Génère un canal chat mock
 */
export const createMockChatChannel = (companyId: string = 'company_1'): ChatChannel => ({
  id: 'chat_1',
  experience_id: 'exp_chat_123',
  experience_name: 'Test Chat Channel',
  ban_media: false,
  ban_urls: false,
  who_can_post: 'members',
  who_can_react: 'members',
  user_posts_cooldown_seconds: 60,
  banned_words: ['badword1', 'badword2'],
});
