import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';


 export function generateSecureApiKey(): string {
  
  const key  = randomBytes(32).toString('hex');

  return  key ;
}

/**
 * Vérifie si une clé fournie est valide
 */








// ⚠️ À METTRE DANS VOTRE .ENV (32 caractères exactement pour AES-256)
const ENCRYPTION_KEY = "votre_cle_ultra_secrete_de_32_ch"; 
const IV_LENGTH = 16; // Vecteur d'initialisation

/**
 * CHIFFRER l'API Key avant le stockage
 */






// ⚠️ À stocker dans votre .env (peut être de n'importe quelle longueur)
const API_SECRET_KEY = "votre_cle_privee_tres_longue_et_secrete";

/**
 * Génère un HMAC pour une clé API (Rapide et sûr)
 */
export const hashApiKey = (apiKey: string): string => {
  return createHmac('sha256', API_SECRET_KEY)
    .update(apiKey)
    .digest('hex');
};

/**
 * Vérifie la clé API reçue
 */
export const verifyApiKey = (incomingApiKey: string, storedHash: string): boolean => {
  const incomingHash = hashApiKey(incomingApiKey);
  
  // Utilisation de timingSafeEqual pour éviter les attaques temporelles
  return timingSafeEqual(
    Buffer.from(incomingHash, 'hex'),
    Buffer.from(storedHash, 'hex')
  );
};

