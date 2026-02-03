// test/mainTest.ts
import { describe, before, after } from 'node:test';
import { clearTestDatabase, seedTestDatabase } from './utils/db.js';

describe('Suite de tests d\'intégration globale', () => {

  before(async () => {
    console.log('--- Initialisation de la base de données de test ---');
    await clearTestDatabase();
    await seedTestDatabase();
  });

 

  
});