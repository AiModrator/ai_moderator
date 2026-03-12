import axios, { AxiosInstance } from 'axios';

export interface AiTranslatorClientConfig {
  minDelay?: number; // ms
  maxDelay?: number; // ms
  blockedInputs?: string[]; // inputs qui provoquent une erreur
}

export class MockAiTranslatorClient  {
  private config: Required<AiTranslatorClientConfig>;
  
  // Required AxiosInstance properties (mocked)
  defaults = axios.defaults;
  interceptors = axios.interceptors;
  request = axios.request;
  get = axios.get;
  delete = axios.delete;
  head = axios.head;
  options = axios.options;
  put = axios.put;
  patch = axios.patch;
  getUri = axios.getUri;

  constructor(config: AiTranslatorClientConfig = {}) {
    this.config = {
      minDelay: config.minDelay ?? 50,
      maxDelay: config.maxDelay ?? 200,
      blockedInputs: config.blockedInputs ?? ['BLOCKED_CONTENT', 'FORBIDDEN'],
    };
  }

  /**
   * Simule un appel API POST avec délai réseau
   * @param path - Le chemin API (ignoré pour le mock)
   * @param inputs - Liste de contenus à traduire
   * @returns Promise<string[]> - Les mêmes inputs après délai
   * @throws Error si un input est dans la liste bloquée
   */
  async post(path: string, inputs: string[]): Promise<string[]> {
    // Simuler un délai réseau aléatoire
    const delay = Math.random() * (this.config.maxDelay - this.config.minDelay) + this.config.minDelay;
    await this.sleep(delay);

    // Vérifier si un input est bloqué
    for (const input of inputs) {
      if (this.config.blockedInputs.includes(input)) {
        throw new Error(`Translation failed: "${input}" is blocked or forbidden`);
      }
    }

    // Retourner les mêmes inputs (mock)
    return inputs;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Permet de reconfigurer les délais à la volée
   */
  setConfig(config: Partial<AiTranslatorClientConfig>): void {
    this.config = { ...this.config, ...config };
  }
}
