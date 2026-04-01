import dotenv from 'dotenv';

// Charger les variables d'environnement de test
dotenv.config({ path: '.env.test' });

// Variables globales de test
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = 'silent';

// Mock Redis pour les tests
jest.mock('ioredis', () => {
  return jest.fn(() => ({
    get: jest.fn().mockResolvedValue(null),
    set: jest.fn().mockResolvedValue('OK'),
    del: jest.fn().mockResolvedValue(1),
    exists: jest.fn().mockResolvedValue(0),
    incr: jest.fn().mockResolvedValue(1),
    expire: jest.fn().mockResolvedValue(1),
    on: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    quit: jest.fn(),
  }));
});

// Configuration globale pour les tests
jest.setTimeout(30000);

// Cleanup après chaque test
afterEach(() => {
  jest.clearAllMocks();
});
