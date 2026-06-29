# Node image to run the Vite dev server.
FROM node:20-alpine

WORKDIR /app

# Install dependencies first (cached layer). The * makes the lock file optional.
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the frontend source.
COPY . .

EXPOSE 5173

# Dev server, reachable from outside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
