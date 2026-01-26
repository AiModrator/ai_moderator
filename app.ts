import 'dotenv/config';
  const { Queue, Worker } = require('bullmq');


import Whop from "@whop/sdk";

const client = new Whop({
  apiKey: process.env.WHOP_API_KEY,
  appID: "app_xxxxxxxxxxxxxx",
});


async function  main() {

  const connection = {
    host: 'localhost',
    port: 6379,
  };

  const repeatbleQueue = new Queue('my-repeatable-jobs', { connection });
  const postQueue = new  Queue('post-jobs' , {connection}) 




  // Upserting a repeatable job in the queue
  await repeatbleQueue.upsertJobScheduler(
    'repeat-every-10s',
    {
      every: 10000, // Job will repeat every 10000 milliseconds (10 seconds)
    },
    {
      name: 'repeatable-job',
    },
  );

  // Worker to process the jobs
  const worker = new Worker(
    'my-repeatable-jobs',
    async (job: { id: any; data: { jobData: any; }; }) => {
      console.log(`Processing job ${job.id} with data: ${job.data.jobData}`);
    },
    { connection },
  );
}



