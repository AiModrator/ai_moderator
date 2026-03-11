// jest.setup.ts
import { config } from 'dotenv';

// Charge le fichier .env
config(); 

// Optionnel : Tu peux forcer des variables spécifiques pour les tests ici
// process.env.DATABASE_URL = "postgresql://..."