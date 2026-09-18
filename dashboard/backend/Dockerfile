FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Card 3a64f98b (17-sep): apt upgrade → deb13u1 — limpia perl CRIT CVE-2026-13221/42496/8376 (SBOM 16-sep)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (as root, before switching user)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and set up permissions
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

ENV HOME=/app

USER appuser

# Copy the rest of the application
COPY --chown=appuser:appgroup . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Protected from Coolify DockerCleanupJob (incident run 105, 18-sep — GO Joker (a))
LABEL coolify.managed=true
