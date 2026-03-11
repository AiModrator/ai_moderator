import { Router } from "express";
import { listForumsController, toggleForumModerationController } from "../controllers/forumController";

const router = Router();

router.get("/forums", listForumsController);
router.patch("/forums/:id/toggle-moderation", toggleForumModerationController);

export default router;
