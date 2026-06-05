FROM node:18-alpine

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Copy package files
COPY --chown=appuser:appgroup package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY --chown=appuser:appgroup . .

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "run", "dev"]