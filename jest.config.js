/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  // Cette ligne permet à Jest de trouver vos fichiers src
  moduleDirectories: ['node_modules', 'src'],
  // Si vous utilisez des imports avec des chemins relatifs complexes
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};