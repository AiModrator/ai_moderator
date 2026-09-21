/**
 * Tâche 07 — DécisionWorker : mapping des erreurs (métier vs infrastructure).
 * Tests unitaires avec dependencies stub (=== === ===).
 */

import { describe, expect, it, vi } from 'vitest';
import type { DecisionJob } from '../../src/types/job.js';
import type { Verdict } from '../../src/types/verdict.js';
import type { ModerationCase, UserActionRecord } from '../../src/types/case.js';
import { DecisionWorker, type DecisionWorkerDeps } from '../../src/queue/decisionWorker.js';
import {
  InvalidJobError,
  CommunityNotFoundError,
  ConfigReadError,
  HistoryWriteError,
} from '../../src/exceptions/index.js';
import { Logger } from '../../src/utils/logger.js';
import { makeDecisionJob } from '../utils/job.js';

const logger = Logger.create('silent');

type PartialDeps = {
  processor?: { processWithEvents: (job: DecisionJob) => Promise<{ verdict: Verdict; userActionEvents: never[] }> };
  communityRepository?: { findByRef: (ref: string) => Promise<unknown> };
  caseRepository?: {
    upsert: (cse: ModerationCase) => Promise<void>;
    updateCallback: (id: string, cb: ModerationCase['callback']) => Promise<void>;
  };
  userActionRepository?: { insertMany: (records: UserActionRecord[]) => Promise<void> };
  callbackClient?: {
    deliver: (url: string, verdict: Verdict) => Promise<{
      status: 'delivered' | 'failed';
      attempts: number;
      lastError: string | null;
      deliveredAt: Date | null;
    }>;
  };
};

function makeWorker(overrides: PartialDeps = {}): { worker: DecisionWorker; deps: PartialDeps } {
  const emptyVerdict: Verdict = {
    moderationCaseId: 'case-1',
    contentId: 'post-42',
    communityRef: 'community-1',
    userRef: 'user-7',
    contentType: 'post',
    status: 'completed',
    decision: 'allow',
    detections: [],
    contentActions: [],
    userActions: [],
    needsReview: false,
  };

  const deps: DecisionWorkerDeps = {
    settings: {
      decisionQueueName: 'decisionQueue',
      decisionWorkerConcurrency: 1,
    } as unknown as DecisionWorkerDeps['settings'],
    queueName: 'decisionQueue',
    communityRepository:
      overrides.communityRepository ?? {
        findByRef: vi.fn().mockResolvedValue({ accountId: 'account-1', callbackUrl: 'https://cb', workflowId: null }),
      },
    processor:
      overrides.processor ?? {
        processWithEvents: vi.fn().mockResolvedValue({ verdict: emptyVerdict, userActionEvents: [] }),
      },
    caseRepository:
      overrides.caseRepository ?? {
        upsert: vi.fn().mockResolvedValue(undefined),
        updateCallback: vi.fn().mockResolvedValue(undefined),
      },
    userActionRepository:
      overrides.userActionRepository ?? {
        insertMany: vi.fn().mockResolvedValue(undefined),
      },
    callbackClient:
      overrides.callbackClient ?? {
        deliver: vi
          .fn()
          .mockResolvedValue({ status: 'delivered', attempts: 1, lastError: null, deliveredAt: new Date() }),
      },
    logger,
  };
  return { worker: new DecisionWorker(deps), deps };
}

describe('DecisionWorker — mapping erreurs', { tags: ['unit'] }, () => {
  it('job invalide → InvalidJobError, rien n’est persisté (pas de retry)', async () => {
    const { worker, deps } = makeWorker();
    await expect(worker.run({ batchId: 42 })).rejects.toBeInstanceOf(InvalidJobError);
    expect(deps.processor.processWithEvents).not.toHaveBeenCalled();
    expect(deps.caseRepository.upsert).not.toHaveBeenCalled();
    expect(deps.callbackClient.deliver).not.toHaveBeenCalled();
  });

  it('communauté inconnue → CommunityNotFoundError propagée, aucune écriture', async () => {
    const { worker, deps } = makeWorker({
      communityRepository: {
        findByRef: vi.fn().mockRejectedValue(new CommunityNotFoundError('community not found: x')),
      },
    });
    await expect(worker.run(makeDecisionJob())).rejects.toBeInstanceOf(CommunityNotFoundError);
    expect(deps.caseRepository.upsert).not.toHaveBeenCalled();
    expect(deps.callbackClient.deliver).not.toHaveBeenCalled();
  });

  it('D-04 injoignable → ConfigReadError propagée (retry BullMQ)', async () => {
    const { worker } = makeWorker({
      communityRepository: {
        findByRef: vi.fn().mockRejectedValue(new ConfigReadError('db down')),
      },
    });
    await expect(worker.run(makeDecisionJob())).rejects.toBeInstanceOf(ConfigReadError);
  });

  it('D-02 injoignable (upsert case) → HistoryWriteError propagée, aucun callback', async () => {
    const { worker, deps } = makeWorker({
      caseRepository: {
        upsert: vi.fn().mockRejectedValue(new HistoryWriteError('mongo down')),
        updateCallback: vi.fn().mockResolvedValue(undefined),
      },
    });
    await expect(worker.run(makeDecisionJob())).rejects.toBeInstanceOf(HistoryWriteError);
    expect(deps.callbackClient.deliver).not.toHaveBeenCalled();
    expect(deps.userActionRepository.insertMany).not.toHaveBeenCalled();
  });

  it('flux nominal : upsert → insertMany(si sanctions) → deliver → updateCallback', async () => {
    const verdict: Verdict = {
      moderationCaseId: 'case-1',
      contentId: 'post-42',
      communityRef: 'community-1',
      userRef: 'user-7',
      contentType: 'post',
      status: 'completed',
      decision: 'action_taken',
      detections: [{ class: 'TOXICITY', score: 0.91, severity: 'HIGH', sources: ['text'] }],
      contentActions: ['DELETE_POST'],
      userActions: ['TIMEOUT_USER'],
      needsReview: false,
    };
    const deps = makeWorker({
      processor: {
        processWithEvents: vi.fn().mockResolvedValue({
          verdict,
          userActionEvents: [{ class: 'TOXICITY', severity: 'HIGH', actions: ['TIMEOUT_USER'] }],
        }),
      },
    });

    await deps.worker.run(makeDecisionJob());

    expect(deps.deps.caseRepository.upsert).toHaveBeenCalledTimes(1);
    expect(deps.deps.userActionRepository.insertMany).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ action: 'TIMEOUT_USER', riskClass: 'TOXICITY', userRef: 'user-7', moderationCaseId: 'case-1' }),
      ])
    );
    expect(deps.deps.callbackClient.deliver).toHaveBeenCalledWith('https://cb', verdict);
    expect(deps.deps.caseRepository.updateCallback).toHaveBeenCalledWith(
      'case-1',
      expect.objectContaining({ status: 'delivered', url: 'https://cb' })
    );
  });

  it('échec de livraison callback → job terminé (pas fatal), statut failed persisté', async () => {
    const { worker, deps } = makeWorker({
      callbackClient: {
        deliver: vi.fn().mockResolvedValue({ status: 'failed', attempts: 3, lastError: 'HTTP 500', deliveredAt: null }),
      },
    });
    await expect(worker.run(makeDecisionJob())).resolves.toBeUndefined();
    expect(deps.caseRepository.updateCallback).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ status: 'failed', attempts: 3, lastError: 'HTTP 500' })
    );
  });
});