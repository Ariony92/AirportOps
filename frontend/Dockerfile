# React development image. Operational scheduling executes in the Python API.
FROM node:22-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
EXPOSE 5173
CMD ["npm", "run", "dev"]
