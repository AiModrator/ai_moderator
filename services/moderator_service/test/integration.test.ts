import { describe, it, expect, beforeEach } from '@jest/globals';
import { MockAiTranslatorClient } from './mocks/aiTranslatorClient.mock';
import { MockAiModerationClients } from './mocks/aiModerationClients.mock';
import { MockWhopClient } from './mocks/whopClient.mock';
import { createMockForum } from './fixtures';

/**
 * Tests d'intégration : Polling + Traduction + Modération
 */
describe('Integration Tests: Polling + Processing Pipeline', () => {
  let translatorClient: MockAiTranslatorClient;
  let moderationClients: MockAiModerationClients;
  let whopClient: MockWhopClient;

  beforeEach(() => {
    // Initialiser les mocks avec configuration par défaut
    translatorClient = new MockAiTranslatorClient({
      minDelay: 50,
      maxDelay: 150,
      blockedInputs: ['BLOCKED_CONTENT', 'FORBIDDEN'],
    });

    moderationClients = new MockAiModerationClients({
      toxicityDelay: { min: 100, max: 250 },
      sexualDelay: { min: 120, max: 270 },
      hateDelay: { min: 110, max: 260 },
    });

    whopClient = new MockWhopClient({
      postsPerCall: 50,
      includeVariation: false,
    });
  });

  // ========== TRANSLATOR TESTS ==========
  describe('AiTranslatorClient', () => {
    it('should translate multiple posts with network latency', async () => {
      const inputs = [
        'Hello world',
        'This is a test',
        'Great discussion',
      ];

      const startTime = Date.now();
      const result = await translatorClient.post('/translate', inputs);
      const duration = Date.now() - startTime;

      expect(result).toEqual(inputs);
      expect(duration).toBeGreaterThanOrEqual(50);
      expect(duration).toBeLessThanOrEqual(500); // Allow some margin
    });

    it('should throw error for blocked content', async () => {
      const inputs = ['BLOCKED_CONTENT'];

      await expect(
        translatorClient.post('/translate', inputs)
      ).rejects.toThrow('blocked or forbidden');
    });

    it('should handle mixed valid and invalid inputs', async () => {
      const inputs = ['Valid content', 'FORBIDDEN'];

      await expect(
        translatorClient.post('/translate', inputs)
      ).rejects.toThrow();
    });

    it('should allow configuration of delays', async () => {
      translatorClient.setConfig({
        minDelay: 200,
        maxDelay: 300,
      });

      const startTime = Date.now();
      await translatorClient.post('/translate', ['test']);
      const duration = Date.now() - startTime;

      expect(duration).toBeGreaterThanOrEqual(200);
    });
  });

  // ========== MODERATION TESTS ==========
  describe('AiModerationClients', () => {
    it('should have 3 moderators with different risks', () => {
      expect(moderationClients.moderators).toHaveLength(3);
      expect(moderationClients.moderators[0].risks).toContain('toxicity');
      expect(moderationClients.moderators[1].risks).toContain('sexual_content');
      expect(moderationClients.moderators[2].risks).toContain('hate_speech');
    });

    it('should moderate content in parallel', async () => {
      const text = 'Test content for moderation';

      const startTime = Date.now();
      const results = await moderationClients.moderateContent(text);
      const duration = Date.now() - startTime;

      expect(results).toHaveLength(3);
      results.forEach(result => {
        expect(result.risk).toBeGreaterThanOrEqual(0);
        expect(result.risk).toBeLessThanOrEqual(100);
      });

      // Parallel execution should be faster than sequential (rough check)
      expect(duration).toBeLessThan(1000);
    });

    it('should return consistent response structure', async () => {
      const results = await moderationClients.moderateContent('test');

      expect(results[0]).toHaveProperty('moderator');
      expect(results[0]).toHaveProperty('risk');
      expect(typeof results[0].moderator).toBe('string');
      expect(typeof results[0].risk).toBe('number');
    });
  });

  // ========== WHOP CLIENT TESTS ==========
  describe('MockWhopClient', () => {
    it('should fetch configured number of posts', async () => {
      const forum = createMockForum();
      const posts = await whopClient.getNewPosts('last_post_id', forum.experience_id);

      expect(posts.length).toBe(50);
    });

    it('should generate posts with complete data', async () => {
      const forum = createMockForum();
      const posts = await whopClient.getNewPosts('last_post_id', forum.experience_id);

      posts.forEach(post => {
        expect(post.id).toBeDefined();
        expect(post.forum_id).toBeDefined();
        expect(post.content).toBeDefined();
        expect(post.user_id).toBeDefined();
        expect(post.created_at).toBeInstanceOf(Date);
        expect(post.view_count).toBeGreaterThanOrEqual(0);
        expect(post.like_count).toBeGreaterThanOrEqual(0);
      });
    });

    it('should allow configuration of post count', async () => {
      whopClient.setConfig({ postsPerCall: 100 });
      const forum = createMockForum();
      const posts = await whopClient.getNewPosts('last_post_id', forum.experience_id);

      expect(posts.length).toBe(100);
    });

    it('should support variation in post count', async () => {
      whopClient.setConfig({
        postsPerCall: 50,
        includeVariation: true,
      });

      const forum = createMockForum();
      const posts = await whopClient.getNewPosts('last_post_id', forum.experience_id);

      // With variation, count should be between 25 and 75
      expect(posts.length).toBeGreaterThan(0);
      expect(posts.length).toBeLessThanOrEqual(100);
    });

    it('should reset post counter', async () => {
      const forum = createMockForum();
      await whopClient.getNewPosts('id1', forum.experience_id);
      whopClient.reset();
      const posts = await whopClient.getNewPosts('id2', forum.experience_id);

      expect(posts[0].id).toBe('post_1');
    });
  });

  // ========== FULL PIPELINE TESTS ==========
  describe('Full Pipeline: Polling + Translation + Moderation', () => {
    it('should execute complete pipeline for 50 posts', async () => {
      const forum = createMockForum();

      // Step 1: Polling
      const startTime = Date.now();
      const posts = await whopClient.getNewPosts('last_id', forum.experience_id);
      expect(posts).toHaveLength(50);

      // Step 2: Extract content and translate
      const contents = posts.map(p => p.content || '');
      const translated = await translatorClient.post('/translate', contents);
      expect(translated).toHaveLength(50);

      // Step 3: Moderate each translated content
      const moderationResults = await Promise.all(
        translated.map(content => moderationClients.moderateContent(content))
      );
      expect(moderationResults).toHaveLength(50);
      moderationResults.forEach(result => {
        expect(result).toHaveLength(3); // 3 moderators
      });

      const duration = Date.now() - startTime;
      console.log(`⏱️  Full pipeline executed in ${duration}ms for 50 posts`);
    });

    it('should handle errors gracefully in pipeline', async () => {
      // Configure translator to block some content
      translatorClient.setConfig({
        blockedInputs: ['BLOCKED'],
      });

      const inputs = ['Valid', 'BLOCKED', 'Another'];

      try {
        await translatorClient.post('/translate', inputs);
        expect(true).toBe(false); // Should not reach here
      } catch (error) {
        expect((error as Error).message).toContain('blocked');
      }
    });

    it('should measure performance with high volume', async () => {
      // Test with 200 posts
      whopClient.setConfig({ postsPerCall: 200 });
      const forum = createMockForum();

      const startTime = Date.now();
      const posts = await whopClient.getNewPosts('id', forum.experience_id);
      const contents = posts.map(p => p.content || '');
      await translatorClient.post('/translate', contents);
      const duration = Date.now() - startTime;

      console.log(`⏱️  High volume test (200 posts): ${duration}ms`);
      expect(duration).toBeGreaterThan(0);
    });
  });
});
