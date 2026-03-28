
import { describe, expect, it } from "vitest";
import { chunking } from "../../src/service/helpers/helpers.js";



describe("test unitaire de tokenizer", () => {
    it('test unitaire de tokenizer', () => {
        const max_tokens = 20;
        const contents = [
            'content 1 ',
            'content 2 ',
            'content 3 ',            
            'content 4 ',
            'content 5 ',            
            'content 6 ', 
        ]
        const {classifiedPosts} = chunking(contents, max_tokens)
        console.log(classifiedPosts)
        expect(classifiedPosts[0].length).toBe(2)
    })
})

