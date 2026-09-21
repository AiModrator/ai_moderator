/**
 * Erreurs métier et d'infrastructure de l'Action Service.
 * Hiérarchie unique : tout hérite d'`ActionServiceError`.
 *
 * Contrat retry (§11 de `main.md`) :
 * - erreurs **d'infrastructure** (`ConfigReadError`, `HistoryWriteError`) → le
 *   worker relance pour laisser BullMQ retenter ;
 * - erreurs **métier** (`InvalidJobError`, `CommunityNotFoundError`) → job `failed`
 *   sans retry.
 */

export class ActionServiceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Job non conforme au contrat (échec Zod) → `failed`, pas de retry. */
export class InvalidJobError extends ActionServiceError {}

/** `communityRef` introuvable en D-04 → `failed`, pas de retry. */
export class CommunityNotFoundError extends ActionServiceError {}

/** D-04 injoignable ou lecture impossible → retry BullMQ. */
export class ConfigReadError extends ActionServiceError {}

/** D-02 (MongoDB) injoignable ou écriture impossible → retry BullMQ. */
export class HistoryWriteError extends ActionServiceError {}

/** Livraison du callback échouée (gérée par CallbackClient, jamais fatale). */
export class CallbackError extends ActionServiceError {}