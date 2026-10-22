# Build the real C++ simulation engine for the browser.
FROM emscripten/emsdk:latest AS wasm
WORKDIR /project/engine
COPY engine/ .
RUN bash ./build-wasm.sh

FROM node:22-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
COPY --from=wasm /project/frontend/public/wasm/ ./public/wasm/
EXPOSE 5173
CMD ["npm","run","dev"]
