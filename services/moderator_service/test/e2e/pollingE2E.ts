
import { startAllWorkers } from '../../src/service/worker/worker';
import { prisma } from '../../src/config/prismaClient';
import { forumPollingQueue, schedulerQueue, contentQueue, connection } from '../../src/service/queue/queue';

// --- MOCK DATA ---
const MOCK_USER_ID = 'user_e2e_test';
const MOCK_COMPANY_ID = 'company_e2e_test';
const MOCK_FORUM_ID = 'forum_e2e_test';
const MOCK_EXPERIENCE_ID = 'exp_e2e_test';
const MOCK_NEW_POST_ID = 'post_e2e_new';

// --- MOCK WHOP CLIENT ---
const mockWhopClient = {
    getNewPost: async (lastId: string | null, expId: string) => {
        // console.log(`[MockWhopClient] getNewPost called. LastId: ${lastId}, ExpId: ${expId}`);
        if (expId === MOCK_EXPERIENCE_ID) {
            return [{ id: MOCK_NEW_POST_ID, content: 'E2E Test Content' }];
        }
        return [];
    }
};

async function setupE2EData() {
    console.log('--- Setting up E2E Data ---');
    // Cleanup prior run
    try {
        await prisma.post.deleteMany({ where: { forum_id: MOCK_FORUM_ID } });
        await prisma.forum.deleteMany({ where: { id: MOCK_FORUM_ID } });
        await prisma.company.deleteMany({ where: { id: MOCK_COMPANY_ID } });
        await prisma.user.deleteMany({ where: { id: MOCK_USER_ID } });
    } catch (e) {
        console.log('Cleanup: No data to clean.');
    }

    // Create User
    await prisma.user.create({
        data: {
            id: MOCK_USER_ID,
            username: 'E2EUser',
            name: 'E2E User',
            created_at: new Date(),
        }
    });

    // Create Company
    await prisma.company.create({
        data: {
            id: MOCK_COMPANY_ID,
            title: 'E2E Company',
            created_at: new Date(),
            updated_at: new Date(),
            user_id: MOCK_USER_ID,
        }
    });

    // Create Forum
    await prisma.forum.create({
        data: {
            id: MOCK_FORUM_ID,
            experience_id: MOCK_EXPERIENCE_ID,
            experience_name: 'E2E Forum',
            company_id: MOCK_COMPANY_ID,
            last_polled_at: new Date(Date.now() - 1000000), // Old date to ensure polling
            polling_failed: false,
            last_external_post_id: 'initial_post_id',
        }
    });
    console.log('--- E2E Data Setup Complete ---');
}

async function runE2ETest() {
    console.log('--- Starting E2E Polling Test (Real Redis) ---');

    try {
        await setupE2EData();

        // 1. Start Workers with Mock Whop Client
        console.log('Starting Workers...');
        startAllWorkers(mockWhopClient);

        // 2. Trigger the Scheduler Job manually (to avoid waiting for the interval)
        // We add a job to the schedulerQueue. The scheduler worker will pick it up.
        console.log('Triggering Scheduler...');
        await schedulerQueue.add('forumPollingScheduler', {});

        // 3. Wait for Processing
        // We poll the DB to check if the record is updated.
        console.log('Waiting for processing (max 10s)...');

        let success = false;
        for (let i = 0; i < 20; i++) { // 10 seconds check loop
            const forum = await prisma.forum.findUnique({ where: { id: MOCK_FORUM_ID } });

            if (forum && forum.last_external_post_id === MOCK_NEW_POST_ID) {
                console.log('✅ DB Updated!');
                success = true;
                break;
            }
            // Wait 500ms
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        let output = '';
        if (success) {
            console.log('✅ SUCCESS: Full flow executed. Scheduler -> Polling -> DB Update.');
            output += '✅ SUCCESS: Full flow executed. Scheduler -> Polling -> DB Update.\n';
        } else {
            console.error('❌ FAILURE: DB was not updated within timeout.');
            output += '❌ FAILURE: DB was not updated within timeout.\n';

            // Debug info: Check Queue counts
            const waiting = await contentQueue.getWaitingCount();
            const active = await contentQueue.getActiveCount();
            const failed = await contentQueue.getFailedCount();
            console.log(`Queue Stats - Waiting: ${waiting}, Active: ${active}, Failed: ${failed}`);
        }

        console.log('TEST_RESULT_START');
        console.log(output);
        console.log('TEST_RESULT_END');

    } catch (error) {
        console.error('Test Failed:', error);
    } finally {
        console.log('--- Cleanup ---');
        // Clean Queues
        await forumPollingQueue.drain();
        await schedulerQueue.drain();
        await contentQueue.drain();

        // Clean Data
        await prisma.post.deleteMany({ where: { forum_id: MOCK_FORUM_ID } });
        await prisma.forum.deleteMany({ where: { id: MOCK_FORUM_ID } });
        await prisma.company.deleteMany({ where: { id: MOCK_COMPANY_ID } });
        await prisma.user.deleteMany({ where: { id: MOCK_USER_ID } });

        // Disconnect
        await connection.quit();
        await prisma.$disconnect();

        // Force exit because listeners keep process alive
        process.exit(0);
    }
}

runE2ETest();
