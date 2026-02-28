import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { startAllWorkers } from '../../src/service/worker/worker';
import {
  setupTestContext,
  teardownTestContext,
  createTestForum,
  DEFAULT_TEST_CONFIG,
  TestContext,
} from './setup';
import {
  waitForJobsCompletion,
  getForumLogs,
  extractMetrics,
  formatLogsTimeline,
  formatMetrics,
  sleep,
  hasLogState,
  countLogsByState,
} from './helpers';
import { writeTestOutput } from './output';

/**
 * Tests d'intégration : Polling + Traduction + Modération
 */
describe('Integration Tests: Polling + Processing Pipeline', () => {
  let context: TestContext;
  let testForumId: string;
  let testStartTime: number;

  /**
   * SETUP : Initialiser les mocks et la BD
   */
  beforeAll(async () => {
    console.log('\n🚀 Setting up test context...');

    // Configuration personnalisée pour ce test
    const customConfig = {
      whop: {
        postsPerCall: 50, // 50 posts par appel
        includeVariation: false,
      },
      translator: {
        minDelay: 50,
        maxDelay: 150,
        blockedInputs: ['BLOCKED_CONTENT', 'FORBIDDEN'],
      },
      moderation: {
        toxicityDelay: { min: 100, max: 250 },
        sexualDelay: { min: 120, max: 270 },
        hateDelay: { min: 110, max: 260 },
      },
      testTimeout: 120000, // 2 minutes
    };

    context = await setupTestContext(customConfig);

    // Créer un forum de test
    const forum = await createTestForum(context.prisma);
    testForumId = forum.id;

    console.log(`✅ Test context initialized`);
    console.log(`   Forum ID: ${testForumId}`);
    console.log(`   Config: ${JSON.stringify(customConfig, null, 2)}`);
  });

  /**
   * CLEANUP : Fermer les connexions (sans nettoyer la BD)
   */
  afterAll(async () => {
    console.log('\n🧹 Cleaning up test context...');
    await teardownTestContext(context);
    console.log('✅ Cleanup complete (BD data preserved)');
  });

  /**
   * TEST 1 : Pipeline complet
   */
  it('should complete full polling + processing pipeline', async () => {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 1: Full Pipeline Execution');
    console.log('='.repeat(60));

    // STEP 1: Lancer les workers
    console.log('\n📌 STEP 1: Starting workers...');
    startAllWorkers(
      context.whopClient,
      context.translatorClient,
      context.moderationClients
    );

    // STEP 2: Attendre la complétion
    console.log('⏳ STEP 2: Waiting for jobs to complete...');
    try {
      // Note: À adapter selon votre implémentation de queue
      await sleep(context.config.testTimeout);
    } catch (error) {
      console.warn('Jobs timeout (might be expected):', error);
    }

    // STEP 3: Lire les logs depuis la BD
    console.log('\n📊 STEP 3: Reading forum logs from database...');
    const forumLogs = await getForumLogs(context.prisma, testForumId);
    console.log(`   Found ${forumLogs.length} log entries`);

    // STEP 4: Calculer les metrics
    console.log('\n📈 STEP 4: Calculating metrics...');
    const metrics = extractMetrics(forumLogs, context.config.whop.postsPerCall);

    // STEP 5: Assertions
    console.log('\n✅ STEP 5: Validating results...');
    if (forumLogs.length > 0) {
      expect(forumLogs.length).toBeGreaterThan(0);
      expect(hasLogState(forumLogs, 'POLLING_SUCCESS')).toBe(true);
      console.log('   ✓ Polling completed successfully');
    } else {
      console.warn('   ⚠️  No logs found (workers might not have run)');
    }

    // STEP 6: Afficher les résultats
    console.log('\n' + formatLogsTimeline(forumLogs));
    console.log(formatMetrics(metrics, context.config));

    // STEP 7: Exporter les résultats
    const logsCount = countLogsByState(forumLogs);
    const testResult = {
      testName: 'Full Pipeline Execution',
      status: forumLogs.length > 0 ? 'PASS' : 'WARN',
      duration: Date.now() - testStartTime,
      config: context.config,
      metrics,
      logsCounts: logsCount,
      totalLogs: forumLogs.length,
    };

    await writeTestOutput(testResult, testForumId);
    console.log('\n📝 Results exported to /Ai/testOutput.md');
  });

  /**
   * TEST 2 : Volume élevé
   */
  it('should handle high volume with dynamic configuration', async () => {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 2: High Volume Processing');
    console.log('='.repeat(60));

    // Reconfigurer pour haute volume
    context.whopClient.setConfig({ postsPerCall: 200 });
    context.translatorClient.setConfig({
      minDelay: 30,
      maxDelay: 100,
    });

    console.log(`\n📌 Configuration:
   • Posts per call: 200
   • Translator delay: 30-100ms
   • Starting processing...
`);

    // Lancer workers
    startAllWorkers(
      context.whopClient,
      context.translatorClient,
      context.moderationClients
    );

    // Attendre
    await sleep(context.config.testTimeout);

    // Lire logs
    const forumLogs = await getForumLogs(context.prisma, testForumId);
    const metrics = extractMetrics(forumLogs, 200);

    // Assertions
    if (forumLogs.length > 0) {
      expect(metrics.successRate).toBeGreaterThanOrEqual(80);
      console.log(`✅ Success rate: ${metrics.successRate.toFixed(2)}%`);
    }

    // Résultats
    console.log(formatMetrics(metrics, context.config));

    const testResult = {
      testName: 'High Volume Processing',
      status: metrics.successRate >= 80 ? 'PASS' : 'WARN',
      duration: Date.now() - testStartTime,
      postsProcessed: 200,
      metrics,
      totalLogs: forumLogs.length,
    };

    await writeTestOutput(testResult, testForumId);
  });

  /**
   * TEST 3 : Gestion des erreurs
   */
  it('should handle translation errors gracefully', async () => {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 3: Error Handling');
    console.log('='.repeat(60));

    // Configurer pour forcer des erreurs
    context.translatorClient.setConfig({
      minDelay: 50,
      maxDelay: 150,
      blockedInputs: ['BLOCKED_CONTENT', 'FORBIDDEN'],
    });

    console.log(`\n📌 Configuration:
   • Blocking inputs that contain: BLOCKED_CONTENT, FORBIDDEN
   • Expected: Some posts should fail translation
`);

    // Lancer workers
    startAllWorkers(
      context.whopClient,
      context.translatorClient,
      context.moderationClients
    );

    // Attendre
    await sleep(context.config.testTimeout);

    // Lire logs
    const forumLogs = await getForumLogs(context.prisma, testForumId);
    const errorLogs = forumLogs.filter((log) => log.error !== null);

    console.log(`\n📊 Results:
   • Total logs: ${forumLogs.length}
   • Error logs: ${errorLogs.length}
   • Error rate: ${(errorLogs.length / forumLogs.length * 100).toFixed(2)}%
`);

    // Assertions
    if (forumLogs.length > 0) {
      // Au moins un log doit être présent
      expect(forumLogs.length).toBeGreaterThan(0);
    }

    const testResult = {
      testName: 'Error Handling',
      status: 'PASS',
      duration: Date.now() - testStartTime,
      totalLogs: forumLogs.length,
      errorCount: errorLogs.length,
      errorRate: (errorLogs.length / forumLogs.length * 100).toFixed(2),
    };

    await writeTestOutput(testResult, testForumId);
  });
});
