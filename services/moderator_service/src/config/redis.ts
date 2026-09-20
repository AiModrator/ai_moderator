import Redis from 'ioredis';


export const connectionRedis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: Number(process.env.REDIS_PORT) || 6379,
  maxRetriesPerRequest: null,
  // Optionnel : Limiter les tentatives de reconnexion pour ne pas saturer les logs
  retryStrategy(times) {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
});

// --- Gestion des erreurs ---
connectionRedis.on('error', (err) => {
  console.error('❌ Erreur de connexion Redis :', err.message);
  throw err ; 
});

connectionRedis.on('connect', () => {
  console.log('✅ Connecté à Redis avec succès !');
});





export async function checkRedisConnection() {
  try {
    // La commande 'ping' est le standard pour vérifier la santé de Redis
    const status = await connectionRedis.ping();
    if (status === 'PONG') {
      console.log('✅ Redis Pong : Connexion établie et opérationnelle.');
    }
  } catch (error) {
    console.error('❌ Impossible de joindre Redis au démarrage :', error);
    // Dans un environnement de production ou de test critique, on force l'arrêt
    process.exit(1); 
  }
}