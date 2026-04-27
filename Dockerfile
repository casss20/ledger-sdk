# Citadel Governance API
# Production-ready container for the governance kernel

FROM python:3.12-slim-bookworm

# Security: run as non-root
RUN groupadd -r citadel && useradd -r -g citadel citadel

# Install dependencies
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY apps/runtime/ ./apps/runtime/
COPY db/ ./db/
COPY migrations/ ./migrations/

# Install with all production dependencies
RUN pip install --no-cache-dir -e ".[all]"

# Ensure the non-root user can read the application code
RUN chown -R citadel:citadel /app

# Security: remove build artifacts
RUN rm -rf /root/.cache /tmp/*

# Make the citadel package importable from the container layout
ENV PYTHONPATH=/app/apps/runtime

# Switch to non-root user
USER citadel

# Expose API port
EXPOSE 8000

# Health check — readiness endpoint (validates DB connectivity)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health/ready')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "citadel.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
