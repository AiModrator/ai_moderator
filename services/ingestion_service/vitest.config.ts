// vitest.config.ts
import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'

export default defineConfig({
  test: {
    // Permet d'utiliser 'describe', 'it', 'expect' sans les importer
    globals: true,
    // Environnement par défaut pour Node.js
    environment: 'node',
    env: loadEnv('', process.cwd(), ''),
    // Les tests d'intégration partagent Redis et Postgres de dev et font du
    // flush/cleanup globaux : on force l'exécution séquentielle des fichiers
    // pour éviter toute interférence entre suites parallèles.
    fileParallelism: false,
    // Tags de classification imposés par les règles du projet
    // (unit / integration / e2e). Filtrage : vitest --tagsFilter integration
    tags: [
      { name: 'unit', description: 'tests unitaires : aucune dépendance externe' },
      { name: 'integration', description: "tests d'intégration : dépendances réelles (Redis, Postgres, Queue)" },
      { name: 'e2e', description: 'tests bout-en-bout via scripts (curl)' },
    ],
  },
})