import { Queue } from 'bullmq';
import { ForumLogState, PrismaClient } from '../../../generated/client';
import { schedulerQueue } from 'src/service/queue/queue';
/**
 * Attendre que tous les jobs d'une queue se terminent
 */
export async function waitForJobsCompletion(
  queue: Queue,
  timeoutMs: number = 60000
): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const jobCounts = await queue.getJobCounts();
    const activeCount = jobCounts.active || 0;
    const waitingCount = jobCounts.waiting || 0;

    if (activeCount === 0 && waitingCount === 0) {
      console.log('✅ All jobs completed');
      return;
    }

    console.log(
      `⏳ Waiting for jobs: ${activeCount} active, ${waitingCount} waiting`
    );
    await sleep(500);
  }

  throw new Error(`Timeout waiting for jobs to complete (${timeoutMs}ms)`);
}

/**
 * Lire tous les logs d'un forum depuis la BD
 */
export async function getForumLogs(
  prisma: PrismaClient,
  forumId: string
): Promise<any[]> {
  return await prisma.forumLogs.findMany({
    where: { forum_id: forumId },
    orderBy: { created_at: 'asc' },
  });
}

/**
 * Extraire les metrics des logs
 */
export interface ForumMetrics {
  totalDuration: number;
  states: {
    state: string;
    count: number;
    avgDuration: number;
    firstOccurrence: Date;
    lastOccurrence: Date;
  }[];
  totalErrors: number;
  retries: number;
  successRate: number;
  throughput: number; // posts/sec
}

export function extractMetrics(
  logs: any[],
  totalPostsProcessed: number = 0
): ForumMetrics {
  if (logs.length === 0) {
    return {
      totalDuration: 0,
      states: [],
      totalErrors: 0,
      retries: 0,
      successRate: 0,
      throughput: 0,
    };
  }

  const startTime = logs[0].created_at;
  const endTime = logs[logs.length - 1].created_at;
  const totalDuration = endTime.getTime() - startTime.getTime();

  // Grouper par state
  const stateMap = new Map<string, any[]>();
  logs.forEach((log) => {
    if (!stateMap.has(log.state)) {
      stateMap.set(log.state, []);
    }
    stateMap.get(log.state)!.push(log);
  });

  // Calculer stats par state
  const states = Array.from(stateMap.entries()).map(([state, stateLogs]) => ({
    state,
    count: stateLogs.length,
    avgDuration:
      stateLogs.reduce((sum, log) => sum + log.duration_ms, 0) / stateLogs.length,
    firstOccurrence: stateLogs[0].created_at,
    lastOccurrence: stateLogs[stateLogs.length - 1].created_at,
  }));

  // Compter erreurs et retries
  const totalErrors = logs.filter((log) => log.error !== null).length;
  const retries = logs.filter((log) => log.isRetry === true).length;

  // Calculer taux de succès
  const successLogs = logs.filter((log) => !log.state.includes('FAILED'));
  const successRate =
    logs.length > 0 ? (successLogs.length / logs.length) * 100 : 0;

  // Calculer throughput
  const throughput =
    totalDuration > 0 ? (totalPostsProcessed / (totalDuration / 1000)) * 1000 : 0;

  return {
    totalDuration,
    states,
    totalErrors,
    retries,
    successRate,
    throughput,
  };
}

/**
 * Formatter les logs pour affichage
 */
export function formatLogsTimeline(logs: any[]): string {
  if (logs.length === 0) return 'No logs found';

  const startTime = logs[0].created_at;
  let output = '📊 Timeline:\n';

  logs.forEach((log, index) => {
    const elapsed = log.created_at.getTime() - startTime.getTime();
    const state = log.state;
    const duration = log.duration_ms.toFixed(2);
    const error = log.error ? ` ❌ ${log.error}` : '';
    const retry = log.isRetry ? ' 🔄 RETRY' : '';

    output += `  ${index + 1}. [${elapsed}ms] ${state} (${duration}ms)${retry}${error}\n`;
  });

  return output;
}

/**
 * Afficher les metrics formatées
 */
export function formatMetrics(metrics: ForumMetrics, config: any): string {
  const duration = (metrics.totalDuration / 1000).toFixed(2);

  let output = `
╔════════════════════════════════════════════════════╗
║        📈 INTEGRATION TEST METRICS                 ║
╚════════════════════════════════════════════════════╝

📋 Configuration:
  • Posts per call: ${config.whop.postsPerCall}
  • Translator delay: ${config.translator.minDelay}-${config.translator.maxDelay}ms
  • Test timeout: ${config.testTimeout}ms

⏱️  Execution:
  • Total duration: ${duration}s
  • States processed: ${metrics.states.length}
  • Total errors: ${metrics.totalErrors}
  • Retries: ${metrics.retries}
  • Success rate: ${metrics.successRate.toFixed(2)}%

📊 Throughput:
  • Posts/sec: ${metrics.throughput.toFixed(2)}

📍 States Timeline:
`;

  metrics.states.forEach((state) => {
    output += `
  ${state.state}:
    - Count: ${state.count}
    - Avg duration: ${state.avgDuration.toFixed(2)}ms
    - First: ${state.firstOccurrence.toISOString()}
    - Last: ${state.lastOccurrence.toISOString()}
`;
  });

  return output;
}

/**
 * Utilitaire : sleep
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Vérifier si log contient un état spécifique
 */
export function hasLogState(logs: any[], state: ForumLogState): boolean {
  return logs.some((log) => log.state === state);
}

/**
 * Compter logs par état
 */
export function countLogsByState(logs: any[]): Record<string, number> {
  const counts: Record<string, number> = {};
  logs.forEach((log) => {
    counts[log.state] = (counts[log.state] || 0) + 1;
  });
  return counts;
}



 export const setupForumPollingSchedulerTest = async () => {
    // On ajoute le job sans l'option "repeat"
    await schedulerQueue.add(
        'forumPollingScheduler', // Gardez le même nom si votre worker écoute ce nom
        {},
        {
            // Pas de propriété 'repeat' ici
            removeOnComplete: true, // Optionnel : nettoie le job une fois fini
            attempts: 1             // Optionnel : ne pas réessayer en cas d'échec pour un test
        }
    );

    console.log('Test unique du forum polling ajouté à la file.');
};