/**
 * Erreurs métier et d'infrastructure typées de l'Ingestion Service.
 * Hiérarchie unique : toutes les classes héritent d'`ApiError`.
 */

export class ApiError extends Error {
  public readonly statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    Object.setPrototypeOf(this, new.target.prototype);
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }
}

/**
 * 400 — le payload ne respecte pas le contrat de validation.
 */
export class ValidationError extends ApiError {
  public readonly fields: string[];

  constructor(message: string, fields: string[] = []) {
    super(message, 400);
    this.fields = fields;
  }
}

/**
 * 401 — la clé API est absente, inconnue ou révoquée.
 */
export class AuthenticationError extends ApiError {
  constructor(message: string = 'Invalid API key') {
    super(message, 401);
  }
}

/**
 * Erreur d'infrastructure Redis (connexion, commande).
 */
export class RedisError extends ApiError {
  constructor(message: string) {
    super(`Redis error: ${message}`, 500);
  }
}

/**
 * Erreur d'infrastructure de queue BullMQ.
 */
export class QueueError extends ApiError {
  constructor(message: string) {
    super(`Queue error: ${message}`, 500);
  }
}