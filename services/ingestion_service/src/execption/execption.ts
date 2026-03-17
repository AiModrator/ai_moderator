
export class ApiError extends Error {
  public readonly statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.statusCode = statusCode;
    this.name = this.constructor.name;

    // Indispensable en TS pour que 'instanceof' fonctionne correctement
    Object.setPrototypeOf(this, ApiError.prototype);

    // Capture la trace d'appel (V8 uniquement, comme Node.js)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }
}




// Erreur 401 : Non authentifié
export class UnauthorizedError extends ApiError {
  constructor(message: string = "Accès non autorisé") {
    super(message, 401);
  }
}

// Erreur 403 : Interdit (Clé API invalide)
export class ForbiddenError extends ApiError {
  constructor(message: string = "Clé API invalide") {
    super(message, 403);
  }
}
