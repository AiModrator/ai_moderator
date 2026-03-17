import { IModerationClient, IModerationClients } from '../../src/types/types';

export interface ModerationScore {
  risk: number; // Score 0-100
}

export interface AiModerationClientConfig {
  delayMin?: number; // ms
  delayMax?: number; // ms
}

/**
 * Mock d'un client de modération IA
 */
export class MockAiModerationClient implements IModerationClient {
  risks: string[];
  private config: Required<AiModerationClientConfig>;
  private name: string;

  constructor(
    name: string,
    risks: string[],
    config: AiModerationClientConfig = {}
  ) {
    this.name = name;
    this.risks = risks;
    this.config = {
      delayMin: config.delayMin ?? 100,
      delayMax: config.delayMax ?? 300,
    };
  }

  /**
   * Simule l'appel au service de modération
   * @param text - Contenu à modérer
   * @returns Promise<ModerationScore> - Score de risque (0-100)
   */
  async getModeration(text: string): Promise<ModerationScore> {
    // Simuler un délai réseau
    const delay = Math.random() * (this.config.delayMax - this.config.delayMin) + this.config.delayMin;
    await this.sleep(delay);

    // Générer un score aléatoire (simulation)
    const risk = Math.floor(Math.random() * 101);

    return { risk };
  }

  /**
   * Récupère le nom du client (utile pour les logs)
   */
  getName(): string {
    return this.name;
  }

  /**
   * Reconfigurer les délais
   */
  setConfig(config: Partial<AiModerationClientConfig>): void {
    this.config = { ...this.config, ...config };
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Factory pour créer tous les clients de modération
 */
export interface AiModerationClientsConfig {
  toxicityDelay?: { min: number; max: number };
  sexualDelay?: { min: number; max: number };
  hateDelay?: { min: number; max: number };
}

export class MockAiModerationClients implements IModerationClients {
  moderators: IModerationClient[];

  constructor(config: AiModerationClientsConfig = {}) {
    const toxicityConfig = config.toxicityDelay || { min: 100, max: 300 };
    const sexualConfig = config.sexualDelay || { min: 120, max: 280 };
    const hateConfig = config.hateDelay || { min: 110, max: 290 };

    this.moderators = [
      new MockAiModerationClient(
        'Toxicity & Insult Detector',
        ['toxicity', 'insult'],
        { delayMin: toxicityConfig.min, delayMax: toxicityConfig.max }
      ),
      new MockAiModerationClient(
        'Sexual Content Detector',
        ['sexual_content'],
        { delayMin: sexualConfig.min, delayMax: sexualConfig.max }
      ),
      new MockAiModerationClient(
        'Hate Speech Detector',
        ['hate_speech'],
        { delayMin: hateConfig.min, delayMax: hateConfig.max }
      ),
    ];
  }

  /**
   * Récupérer un moderator par index
   */
  getModerator(index: number): IModerationClient {
    return this.moderators[index];
  }

  /**
   * Exécuter la modération en parallèle sur tous les clients
   */
  async moderateContent(text: string): Promise<{ moderator: string; risk: number }[]> {
    const results = await Promise.all(
      this.moderators.map(async (moderator) => ({
        moderator: moderator.getName?.() || 'Unknown',
        risk: (await moderator.getModeration(text)).risk,
      }))
    );
    return results;
  }
}
