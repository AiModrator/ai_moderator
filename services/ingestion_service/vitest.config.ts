// vitest.config.ts
import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'

export default defineConfig({
  test: {
    // Permet d'utiliser 'describe', 'it', 'expect' sans les importer
    globals: true, 
    // Environnement par défaut pour Node.js
    environment: 'node', 
    env: loadEnv('', process.cwd(), '')
  },
})
