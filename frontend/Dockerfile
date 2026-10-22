# IncidentIQ Frontend Dockerfile
# Provides reproducible build and runtime matching root docker-compose.yml

FROM node:20-alpine

WORKDIR /app

# Install dependencies using the committed package-lock.json without modification
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code
COPY . .

# Build validation: compiles production bundle during image build to verify correctness
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Default environment configuration
ENV PORT=5173
EXPOSE 5173

# Startup command: binds to 0.0.0.0 on port 5173 to align with Compose ports: 5173:5173
# Uses Vite server to dynamically read VITE_API_BASE_URL injected by Docker Compose
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
