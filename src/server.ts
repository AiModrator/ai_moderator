import { rootCertificates } from "node:tls";
import { setUserRoute } from "./routes/userRoutes";
import express, { Router } from 'express';

const app = express();
const router = express.Router();
const port = 8000;

export function runServer() {
    console.log('Starting server...');

 
    app.use(express.json());

    // Set up routes BEFORE listening
    setUserRoute(router);
    app.use(router);

    app.listen(port, () => {
        console.log(`Server is running on port ${port}`);
    });
}


