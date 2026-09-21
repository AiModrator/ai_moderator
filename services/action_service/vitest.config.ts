// vitest.config.ts
import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';

export default defineConfig({
  test: {
    // 'describe', 'it', 'expect' disponibles sans import
    globals: true,
    environment: 'node',
    env: loadEnv('', process.cwd(), ''),
    // Les tests d'intégration partagent Postgres, Redis et Mongo : exécution
    // séquentielle des fichiers pour éviter toute interférence.
    fileParallelism: false,
    // Tags imposés par les règles du projet (unit / integration / e2e).
    // Filtrage : vitest --tagsFilter integration
    tags: [
      { name: 'unit', description: 'tests unitaires : aucune dépendance externe' },
      { name: 'integration', description: "tests d'intégration : dépendances réelles (Postgres, Redis, Mongo)" },
      { name: 'e2e', description: 'tests bout-en-bout via scripts' },
    ],
  },
});