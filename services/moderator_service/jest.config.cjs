/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  // Utilisation du preset spécifique ESM de ts-jest
  preset: 'ts-jest/presets/default-esm',
  
  testEnvironment: 'node',
  
  // Indique à Jest de traiter les fichiers .ts comme des modules ES
  extensionsToTreatAsEsm: ['.ts'],
  
  moduleNameMapper: {
    // Gère les imports se terminant par .js vers les fichiers .ts (obligatoire en ESM)
    '^(\\.{1,2}/.*)\\.js$': '$1',
    // Vos alias personnalisés
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@moderator/database$': '<rootDir>/../../database',
    '^@moderator/(.*)$': '<rootDir>/../../$1',
  },

  testMatch: [
    '**/test/**/*.test.ts', 
    '**/test/**/*.integration.ts'
  ],

  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/index.ts',
    '!src/server.ts',
  ],

  coveragePathIgnorePatterns: ['/node_modules/', '/test/'],

  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },

  testTimeout: 30000,

  // setupFilesAfterEnv: ['<rootDir>/test/jest.setup.ts'],

  transform: {
    // Configuration de la transformation ts-jest pour l'ESM
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        useESM: true,
        isolatedModules: true,
        tsconfig: {
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
          resolveJsonModule: true,
          // S'assure que le compilateur TS cible l'ESM pour les tests
          module: 'ESNext',
        },
      },
    ],
  },

  // Ne pas ignorer les modules qui utilisent l'ESM dans node_modules
  transformIgnorePatterns: [
    'node_modules/(?!(@moderator|@prisma|@whop|bullmq)/)'
  ],
};
