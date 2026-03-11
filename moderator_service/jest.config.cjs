/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'node',
  // --- AJOUTE CETTE LIGNE ---
  setupFiles: ['<rootDir>/jest.setup.ts'], 
  // --------------------------
  extensionsToTreatAsEsm: ['.ts'],
  moduleDirectories: ['node_modules', 'src'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        useESM: true,
        isolatedModules: true,
      },
    ],
  },
  forceExit: true,
  testTimeout: 150000,
};