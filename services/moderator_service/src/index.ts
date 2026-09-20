import dotenv from 'dotenv';

// Charger les variables d'environnement AVANT tout le reste
dotenv.config({ path: '.env.local' });
dotenv.config(); // Fallback vers .env

import { setupMainTest } from "../test/setup/setup"

async function main() {
  console.log("route " , process.env.DATABASE_URL)
  await setupMainTest()
}

main().catch(console.error)