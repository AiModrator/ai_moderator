




import { describe, it, expect, beforeEach, vi, beforeAll } from 'vitest';
import prisma, { Phase, Steps } from "@moderator/database";
import { insertLog } from '../../src/models/logs';
import { logsWrapperFactory } from '../../src/utils/wrappers';



describe('Logs Service Tests', () => {

    // On nettoie la table logs avant chaque test pour éviter les interférences
    beforeAll(async () => {
        await prisma.logs.deleteMany();
    });

    describe('insertLog', () => {
        it('devrait insérer un log de succès dans la base de données', async () => {
          
            const duration = 150.5;

            await insertLog(Phase.INGESTION, Steps.WEBHOOK, duration);

            // Vérification dans la DB
            const logInDb = await prisma.logs.findFirst({
                where: { step: Steps.WEBHOOK }
            });

            expect(logInDb).toBeDefined();
            expect(logInDb?.phase).toBe(Phase.INGESTION);
            expect(logInDb?.duration_ms).toBe(duration);
            expect(logInDb?.error).toBeNull();
        });
    });

    describe('logsWrapperFactory', () => {
        it('devrait wrapper une fonction, l\'exécuter et enregistrer le log de durée', async () => {
            // 1. Préparation de la fonction originale (un mock)
            const mockFn = vi.fn().mockResolvedValue("Résultat OK");

            // 2. Création du wrapper
            const wrapper = logsWrapperFactory(Steps.PROCESSING_AI_CALL, Phase.MODERATION);
            const wrappedFn = wrapper(mockFn);

            // 3. Exécution
            const result = await wrappedFn("arg1", "arg2");

            // 4. Assertions
            expect(result).toBe("Résultat OK");
            expect(mockFn).toHaveBeenCalledWith("arg1", "arg2");

            // Vérifier que le log a été inséré
            const logGenerated = await prisma.logs.findFirst({
                where: { step: Steps.PROCESSING_AI_CALL }
            });

            expect(logGenerated).toBeDefined();
            expect(logGenerated?.duration_ms).toBeGreaterThan(0);
        });

        it('devrait capturer l\'erreur et insérer un log d\'échec en cas de throw', async () => {
            // 1. Une fonction qui crash
            const errorMessage = "L'IA ne répond pas";
            const failingFn = vi.fn().mockRejectedValue(new Error(errorMessage));

            const wrapper = logsWrapperFactory(Steps.PROCESSING_AI_CALL, Phase.MODERATION);
            const wrappedFn = wrapper(failingFn);

            // 2. Exécution et capture de l'erreur attendue
            await expect(wrappedFn()).rejects.toThrow(errorMessage);

            // 3. Vérification du log d'erreur
            const errorLog = await prisma.logs.findFirst({
                where: {
                    step: Steps.PROCESSING_AI_CALL,
                    error: errorMessage // On cherche spécifiquement celui avec cette erreur
                },
                orderBy: { created_at: 'desc' } // Le plus récent
            });
            expect(errorLog?.error).toBe(errorMessage);
            expect(errorLog?.duration_ms).toBe(0);
        });
    });
});