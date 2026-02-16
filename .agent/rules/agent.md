

---

# 🤖 GEMINI.md - Directives de Développement

Ce document définit les standards de code et les flux de travail pour ce projet **Express + TypeScript + Prisma**.

## 🛠 Stack Technique

* **Runtime:** Node.js avec TypeScript.
* **Framework:** Express.
* **ORM:** Prisma (Client & Migrations).
* **Architecture:** Layered Architecture (Routes -> Controllers -> Services -> Models/Prisma).

---
## Les fichiers de Ai et context  :
- chemin = /Ai/prompt.md (Le fichier qui contient prompt actuelle)
-chemin =/Ai/testOutput.md (Pour ecrire  les resultat du test)



## 📐 Architecture & Responsabilités

Tu dois strictement respecter la répartition suivante des dossiers :

| Dossier | Responsabilité |
| --- | --- |
| **`/routes`** | Définition des endpoints et injection des middlewares. |
| **`/service`** | Logique métier (Business Logic). C'est ici que les calculs et les règles complexes résident. |
| **`/models`** | Interaction directe avec **Prisma**. Chaque fichier doit gérer les requêtes CRUD spécifiques à une entité. |
| **`/types`** | Interfaces et types TypeScript globaux. |
| **`/config`** | Configuration (Base de données, variables d'environnement). |

---

## 📜 Règles Générales de Code

* **Single Responsibility Principle (SRP) :** Une fonction = une action. Si une fonction dépasse 20 lignes, demande-toi si elle doit être divisée.
* **Clean Code :** Priorise la lisibilité. Utilise des noms de variables explicites.
* **Gestion d'erreurs :** Utilise des blocs `try/catch` et des codes HTTP appropriés (200, 201, 400, 404, 500).
* **Immuabilité :** Ne modifie jamais un fichier existant sans expliquer pourquoi et obtenir mon accord préalable.

---

## 🔄 Workflow de Travail (Obligatoire)

Avant toute modification de code, tu dois suivre ces deux étapes :

## 🔄 Workflow de Travail (Validation Globale)

1. **Phase de Planification :** Pour chaque demande, propose d'abord un plan détaillé (fichiers impactés, logique utilisée).
2. **Approbation Unique :** Une fois que j'ai validé ce plan, tu as l'autorisation d'exécuter **toutes** les modifications mentionnées dans le plan d'un seul coup, sans me redemander confirmation pour chaque fichier ou chaque commande CLI.
3. **Exécution :** Applique les changements de manière autonome après mon "OK".
3. **Test :** : Si ce que etait demainde c'etait du endpoint je veut que tu le teste a l'aide du curl et ecrire le output en testOutuput.md .Ajouter le  le numero du prompt a cote du outuput du test  . 

---

## 🗄️ Spécificités Prisma

* Toujours vérifier le fichier `schema.prisma` avant de proposer une nouvelle requête dans `/models`.
* Si une modification nécessite une migration, mentionne-le clairement dans ton plan.

---
