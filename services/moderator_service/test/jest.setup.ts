import dotenv from 'dotenv';
import { jest, afterEach } from '@jest/globals';


// Charger les variables d'environnement de test
dotenv.config({ path: '.env' });

// Variables globales de test
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = 'silent';

// Mock Redis pour les tests


