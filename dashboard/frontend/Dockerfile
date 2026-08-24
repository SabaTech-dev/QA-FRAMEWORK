FROM node:26-alpine

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Copy package files
COPY --chown=appuser:appgroup package*.json ./

# Install dependencies
# npm 12: enforce del allowlist de install scripts (allowScripts en package.json)
RUN npm install --strict-allow-scripts

# Smoke post-install: fallar el build si el binario nativo no carga
COPY --chown=appuser:appgroup scripts/smoke-install.mjs ./scripts/smoke-install.mjs
RUN node scripts/smoke-install.mjs

# Copy the rest of the application
COPY --chown=appuser:appgroup . .

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "run", "dev"]