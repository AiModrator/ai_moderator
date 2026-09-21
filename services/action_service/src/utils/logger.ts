/**
 * Logger applicatif de l'Action Service — pino (JSON structuré).
 * Jamais de `console.log` dans le code du service.
 */

import pino, { type Logger as PinoLogger } from 'pino';

export class Logger {
  private readonly logger: PinoLogger;

  private constructor(internal: PinoLogger) {
    this.logger = internal;
  }

  /**
   * Fabrique le logger racine. `level` = `trace|debug|info|warn|error|silent`.
   * `LOG_FORMAT=pretty` active pino-pretty pour le développement.
   */
  static create(level?: string): Logger {
    const resolved = level ?? process.env['LOG_LEVEL'] ?? 'info';
    const pretty = process.env['LOG_FORMAT'] === 'pretty';
    const internal = pino({
      level: resolved,
      base: { service: 'action_service' },
      ...(pretty ? { transport: { target: 'pino-pretty', options: { sync: true } } } : {}),
    });
    return new Logger(internal);
  }

  child(bindings: Record<string, unknown>): Logger {
    return new Logger(this.logger.child(bindings));
  }

  debug(message: string, fields?: Record<string, unknown>): void {
    this.logger.debug(fields ?? {}, message);
  }

  info(message: string, fields?: Record<string, unknown>): void {
    this.logger.info(fields ?? {}, message);
  }

  warn(message: string, fields?: Record<string, unknown>): void {
    this.logger.warn(fields ?? {}, message);
  }

  error(message: string, fields?: Record<string, unknown>): void {
    this.logger.error(fields ?? {}, message);
  }
}