import { validateUser } from "./api/getUser";
import express from 'express';

const app = express();
const router = express.Router();
const port = 8000;

export function runServer() {
    console.log('Starting server...');

 
    app.use(express.json());

    // Set up routes BEFORE listening
    setRoutes();
    app.use(router);

    app.listen(port, () => {
        console.log(`Server is running on port ${port}`);
    });
}

function setRoutes() {
    router.post('/api/validateUser', validateUser);
}
