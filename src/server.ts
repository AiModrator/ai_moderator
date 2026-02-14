import { rootCertificates } from "node:tls";
import { setUserRoute } from "./routes/userRoutes";
import express, { Router } from 'express';
import forumRoutes from "./routes/forumRoutes";
import { setupForumPollingScheduler } from "./service/polling/scheduler";
import { startAllWorkers } from "./service/polling/worker";

const app = express();
const router = express.Router();
const port = 8000;

export function runServer() {
    console.log('Starting server...');


    app.use(express.json());

    // Set up routes BEFORE listening
    setUserRoute(router);
    app.use(router);
    app.use(forumRoutes);

    app.listen(port, () => {
        console.log(`Server is running on port ${port}`);
        // Setup polling after server starts
        setupForumPollingScheduler();
        startAllWorkers();
    });
}


