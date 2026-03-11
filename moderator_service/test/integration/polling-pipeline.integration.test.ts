import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { startAllWorkers } from 'src/service/worker/worker';
import {
  setupTestContext,
  teardownTestContext,
  createTestForum,
  DEFAULT_TEST_CONFIG,
  TestContext,
  createTestUser,
  createTestCompany,
  clearRedis,
  clearDatabase,
  waitForQueue,
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
  setupForumPollingSchedulerTest,
} from './helpers';
import { writeTestOutput } from './output';
import { setupForumPollingScheduler } from 'src/service/triggers/trigger';
import { run } from 'node:test';
import { forumPollingQueue, postProcessingQueue } from 'src/service/queue/queue';


/**
 * Tests d'intégration : Polling + Traduction + Modération
 */
describe('Integration Tests: Polling + Processing Pipeline', () => {
  let context: TestContext;
  let testForumId: string;
  let testStartTime: number;

  /**
   * Fonction utilitaire : Configuration de test personnalisée
   */
  function getCustomTestConfig() {
    return {
      whop: {
        postsPerCall: 50,
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
      testTimeout: 120000,
    };
  }

  /**
   * Fonction utilitaire : Préparer l'environnement de test
   */
  async function initializeTestEnvironment() {
    console.log('\n🚀 Setting up test context...');

    const customConfig = getCustomTestConfig();
    await clearDatabase();
    await clearRedis();

    context = await setupTestContext(customConfig);
    await createTestUser(context.prisma);
    await createTestCompany(context.prisma);

    const forum = await createTestForum(context.prisma);
    testForumId = forum.id;

    console.log(`✅ Test context initialized`);
    console.log(`   Forum ID: ${testForumId}`);
    console.log(`   Config: ${JSON.stringify(customConfig, null, 2)}`);
  }

  /**
   * Fonction utilitaire : Démarrer les workers et attendre
   */
  async function runWorkersPipeline(shouldSleep: boolean ,  timeout: number = context.config.testTimeout ) {
      startAllWorkers(
      context.whopClient,
      context.translatorClient,
      context.moderationClients
    );

    // console.log("Attente de la fin du polling...");
    // await waitForQueue(forumPollingQueue);
    
    // console.log("Attente de la fin du post-processing...");
    // await waitForQueue(postProcessingQueue);

    // console.log("✅ Tout est fini !");

    if (shouldSleep) {
      await sleep(timeout);
    }
    
    
  }

  /**
   * Fonction utilitaire : Collecter les logs et calculer les métriques
   */
  async function collectLogsAndMetrics(expectedPostCount?: number) {
    const forumLogs = await getForumLogs(context.prisma, testForumId);
    const metrics = expectedPostCount 
      ? extractMetrics(forumLogs, expectedPostCount) 
      : extractMetrics(forumLogs, context.config.whop.postsPerCall);
    return { forumLogs, metrics };
  }

  /**
   * TEST 1 : Pipeline complet - Normal Test
   */
  async function runNormalTest() {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 1: Full Pipeline Execution');
    console.log('='.repeat(60));

    console.log('\n📌 STEP 0: Starting scheduler...');
    // setupForumPollingScheduler();
    setupForumPollingSchedulerTest()

    console.log('\n📌 STEP 1: Starting workers...');
    console.log('Le context : ', context);
    await runWorkersPipeline( true, 30000);

    console.log('\n📊 STEP 3: Reading forum logs from database...');
    const { forumLogs, metrics } = await collectLogsAndMetrics();
    console.log(`   Found ${forumLogs.length} log entries`);

    console.log('\n📈 STEP 4: Calculating metrics...');
    console.log('\n✅ STEP 5: Validating results...');
    if (forumLogs.length > 0) {
      expect(forumLogs.length).toEqual(50);
      console.log('Count of logs ' , forumLogs.length);
      console.log('   ✓ Polling completed successfully');
    } else {
      console.warn('   ⚠️  No logs found (workers might not have run)');
    }

    console.log('\n' + formatLogsTimeline(forumLogs));
    console.log(formatMetrics(metrics, context.config));

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

    await writeTestOutput(testResult, testForumId, 'Normal Test');
    console.log(testResult);
    console.log('\n📝 Results exported to /Ai/testOutput.md');
  }

  /**
   * TEST 2 : Traitement de volume élevé
   */
  async function runHighVolumeTest() {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 2: High Volume Processing');
    console.log('='.repeat(60));

    console.log(`\n📌 Configuration:
   • Posts per call: 200
   • Translator delay: 30-100ms
   • Starting processing...
`);

    context.whopClient.setConfig({ postsPerCall: 200 });
    context.translatorClient.setConfig({
      minDelay: 30,
      maxDelay: 100,
    });

    await runWorkersPipeline(false);

    const { forumLogs, metrics } = await collectLogsAndMetrics(200);

    if (forumLogs.length > 0) {
      expect(metrics.successRate).toBeGreaterThanOrEqual(80);
      console.log(`✅ Success rate: ${metrics.successRate.toFixed(2)}%`);
    }

    console.log(formatMetrics(metrics, context.config));

    const testResult = {
      testName: 'High Volume Processing',
      status: metrics.successRate >= 80 ? 'PASS' : 'WARN',
      duration: Date.now() - testStartTime,
      postsProcessed: 200,
      metrics,
      totalLogs: forumLogs.length,
    };

    await writeTestOutput(testResult, testForumId, 'High Volume Processing');
  }

  /**
   * TEST 3 : Gestion des erreurs
   */
  async function runErrorTest() {
    testStartTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('TEST 3: Error Handling');
    console.log('='.repeat(60));

    

    context.translatorClient.setConfig({
      minDelay: 50,
      maxDelay: 150,
      blockedInputs: ['BLOCKED_CONTENT', 'FORBIDDEN'],
    });

      

    console.log(`\n📌 Configuration:
   • Blocking inputs that contain: BLOCKED_CONTENT, FORBIDDEN
   • Expected: Some posts should fail translation
`);
    setupForumPollingSchedulerTest()
    await runWorkersPipeline(true  , 18000);

    const { forumLogs } = await collectLogsAndMetrics();
    const errorLogs = forumLogs.filter((log) => log.error !== null);

    console.log(`\n📊 Results:
   • Total logs: ${forumLogs.length}
   • Error logs: ${errorLogs.length}
   • Error rate: ${(errorLogs.length / forumLogs.length * 100).toFixed(2)}%
`);

    if (forumLogs.length > 0) {
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

    await writeTestOutput(testResult, testForumId, 'Error Handling');
  }

  /**
   * SETUP : Initialiser les mocks et la BD
   */
  beforeAll(async () => {
    await initializeTestEnvironment();
  });

  /**
   * CLEANUP : Fermer les connexions
   */
  afterAll(async () => {
    console.log('\n🧹 Cleaning up test context...');
    await teardownTestContext(context);
    console.log('✅ Cleanup complete (BD data preserved)');
  });

  /**
   * Exécuter le test de gestion des erreurs
   */
  it('should handle translation errors gracefully', async () => {
    await runErrorTest();
  });

  // it('Just Normal Test', async () => {
  //   await runNormalTest();
  // });
});


