
export class Worker {
    constructor(name, callback) {
        console.log(`[MockBullMQ] Worker created for ${name}`);
        // Store callback globally or on the class to be accessible
        if (!global.mockWorkerCallbacks) {
            global.mockWorkerCallbacks = {};
        }
        global.mockWorkerCallbacks[name] = callback;
    }
    on() { return this; }
    close() { return Promise.resolve(); }
}

export class Queue {
    constructor(name) {
        this.name = name;
    }
    add(name, data) {
        console.log(`[MockBullMQ] Job added to ${this.name}: ${name}`);
        // Optionally trigger worker immediately?
        // Let's store it so test can verify
        if (!global.mockQueueJobs) {
            global.mockQueueJobs = [];
        }
        global.mockQueueJobs.push({ queue: this.name, name, data });
        return Promise.resolve({ id: 'mock_job' });
    }
    on() { return this; }
    close() { return Promise.resolve(); }
    drain() { return Promise.resolve(); }
}
