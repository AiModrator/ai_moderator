---
trigger: always_on
---

agent_settings:
  yolo_mode: true
  ask_before_delete: false
  auto_approve_commands: 
    # Gestion fichiers
    - "mkdir"
    - "touch"
    - "ls"
    - "cp"
    - "mv"
    # Git
    - "git add ."
    - "git status"
    - "git commit -m"
    # Dépendances et exécution
    - "npm install"
    - "npm run build"
    - "npx"
    # Tests et Debug
    - "npm test"
    - "jest"
    - "curl" # Pour tester vos API localement