
export const prisma = {
    forum: {
        update: async (args) => {
            console.log('[MockPrisma] forum.update called', JSON.stringify(args));
            if (!global.mockPrismaUpdates) global.mockPrismaUpdates = [];
            global.mockPrismaUpdates.push({ model: 'forum', op: 'update', args });
            return args.data;
        },
        findMany: async (args) => {
            console.log('[MockPrisma] forum.findMany called');
            return [];
        }
    },
    post: {
        create: async (args) => Promise.resolve(args.data),
    },
    $disconnect: async () => Promise.resolve(),
};
