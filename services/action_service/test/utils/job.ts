/**
 * Fixtures du job `decisionQueue` (contrat `phase-05/main.md` §2) pour les tests.
 */

import type { DecisionJob } from '../../src/types/job.js';

export function makeDecisionJob(overrides: Partial<DecisionJob> = {}): DecisionJob {
  return {
    batchId: '3f3e8a5a-0b1a-4e4a-9b0a-000000000001',
    communityRef: 'community-1',
    content: {
      contentId: 'post-42',
      contentType: 'post',
      userRef: 'user-7',
      timestamp: '2026-09-21T10:00:00.000Z',
    },
    activeClasses: ['SPAM', 'TOXICITY', 'SEXUAL'],
    status: 'COMPLETE',
    detections: [],
    filtersReport: [
      { filter: 'SpamFilter', status: 'COMPLETED', attempts: 1, error: null },
    ],
    moderatedAt: '2026-09-21T10:00:01.000Z',
    processingMs: 420,
    ...overrides,
  };
}