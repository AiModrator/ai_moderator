import {Redis} from 'ioredis';


export const connectionRedis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: Number(process.env.REDIS_PORT) || 6379,
  maxRetriesPerRequest: null, // OBLIGATOIRE pour BullMQ
});


