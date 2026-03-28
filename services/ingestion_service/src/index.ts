
import app from "./config/express.js";
import { setUpPolling } from "./controllers/polling/polling.js";
import AxiosFactory from "./config/axiosClient.js";
import { setupWebHooksRoutes } from "./controllers/webHooks/webHooks.js";
import { checkRedisConnection, connectionRedis } from "./config/RedisClient.js";
import { checkDbConnection } from "../../../database/prismaClient.js";











function main() {



    try {

        checkDbConnection();
        checkRedisConnection();

        setupWebHooksRoutes(app)

        app.listen(3000, () => {
            console.log('Server is running on port 3000');
        });


        const axiosFactory = new AxiosFactory();

        setUpPolling(axiosFactory, connectionRedis)
    } catch (error) {
        console.error(error)
        process.exit(1)
        // Log the error
    }

}
