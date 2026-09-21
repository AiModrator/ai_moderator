/**
 * Logger applicatif transverse. Enveloppe `console`, ajoute un niveau
 * minimum configurable et un préfixe `[ingestion]`. Format JSON en
 * production (LOG_FORMAT=json), console lisible en dev.
 */

type Level = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_PRIORITY: Record<Level, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

export class Logger {
  private readonly level: Level;
  private readonly json: boolean;

  constructor(level: string = 'info', json: boolean = process.env['LOG_FORMAT'] === 'json') {
    this.level = (['debug', 'info', 'warn', 'error'] as Level[]).includes(level as Level)
      ? (level as Level)
      : 'info';
    this.json = json;
  }

  debug(message: string, fields?: Record<string, unknown>): void {
    this.write('debug', message, fields);
  }

  info(message: string, fields?: Record<string, unknown>): void {
    this.write('info', message, fields);
  }

  warn(message: string, fields?: Record<string, unknown>): void {
    this.write('warn', message, fields);
  }

  error(message: string, fields?: Record<string, unknown>): void {
    this.write('error', message, fields);
  }

  child(bindings: Record<string, unknown>): Logger {
    return new BoundLogger(this, bindings);
  }

  write(level: Level, message: string, fields?: Record<string, unknown>): void {
    if (LEVEL_PRIORITY[level] < LEVEL_PRIORITY[this.level]) return;

    const entry: Record<string, unknown> = {
      level,
      service: 'ingestion_service',
      message,
      ...fields,
    };

    if (this.json) {
      // eslint-disable-next-line no-console
      console[level === 'debug' ? 'log' : level](JSON.stringify(entry));
    } else {
      const suffix = fields ? ` ${JSON.stringify(fields)}` : '';
      // eslint-disable-next-line no-console
      console[level === 'debug' ? 'log' : level](`[ingestion_service] [${level}] ${message}${suffix}`);
    }
  }
}

class BoundLogger extends Logger {
  constructor(
    private readonly parent: Logger,
    private readonly bindings: Record<string, unknown>
  ) {
    super();
  }

  override write(level: Level, message: string, fields?: Record<string, unknown>): void {
    this.parent.write(level, message, { ...this.bindings, ...fields });
  }
}