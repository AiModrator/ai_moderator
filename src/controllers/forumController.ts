import { Request, Response } from "express";
import { toggleForumModeration, listForums } from "../service/forumService";

export async function toggleForumModerationController(req: Request, res: Response) {
    try {
        const { id } = req.params;
        const updatedForum = await toggleForumModeration(id);
        res.status(200).json(updatedForum);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Internal Server Error" });
    }
}

export async function listForumsController(req: Request, res: Response) {
    try {
        const forums = await listForums();
        res.status(200).json(forums);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Internal Server Error" });
    }
}
