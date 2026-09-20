FROM node:22-alpine

WORKDIR /app

# Installation des dépendances du workspace (monorepo : database + services)
COPY package*.json ./
COPY database/package.json ./database/
COPY services/ingestion_service/package.json ./services/ingestion_service/
COPY services/action_service/package.json ./services/action_service/
RUN npm install

# Copie des sources du monorepo
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "-w", "ingestion_service"]