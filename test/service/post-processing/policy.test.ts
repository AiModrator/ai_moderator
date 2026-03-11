
import { deepStrictEqual } from 'assert';
import { describe, it } from 'mocha';
import sinon from 'sinon';
import { resolveUserPolicy } from '../../../src/service/post-processing/policy';
import { Degre } from '../../../generated/enums';

describe('Policy Resolver', () => {
    it('should resolve user policy and format risks correctly', async () => {
        const forumId = 'f1';
        const mockRegles = [
            {
                id: 1,
                risque_id: 1,
                customized_risque_id: null,
                forum_id: forumId,
                degre: Degre.HIGH,
                company_id: null,
                risque: { id: 1, nom: 'Standard Risk', description: 'A standard risk description.' },
                customized_risque: null,
            },
            {
                id: 2,
                risque_id: null,
                customized_risque_id: 1,
                forum_id: forumId,
                degre: Degre.LOW,
                company_id: 'c1',
                risque: null,
                customized_risque: { id: 1, nom: 'Custom Risk', description: 'A custom risk description.', company_id: 'c1' },
            },
        ];

        const getRisksForForumStub = sinon.stub().withArgs(forumId).resolves(mockRegles);

        const result = await resolveUserPolicy(forumId, getRisksForForumStub);

        const expected = {
            risks: [
                { risque: 'Standard Risk', description: 'A standard risk description.' },
                { risque: 'Custom Risk', description: 'A custom risk description.' },
            ],
            forumContext: 'A standard risk description. A custom risk description.',
        };

        deepStrictEqual(result.risks.sort((a,b)=> a.risque.localeCompare(b.risque)), expected.risks.sort((a,b)=> a.risque.localeCompare(b.risque)));
        deepStrictEqual(result.forumContext, expected.forumContext);
        sinon.assert.calledWithExactly(getRisksForForumStub, forumId);
    });
});
