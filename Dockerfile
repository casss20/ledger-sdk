# Citadel Governance API
# Production-ready container for the governance kernel

FROM python:3.12-slim-bookworm

# Security: run as non-root
RUN groupadd -r citadel && useradd -r -g citadel citadel

# Install dependencies
WORKDIR /app
COPY pyproject.toml README.md ./
COPY apps/runtime/ ./apps/runtime/
COPY demo/ ./demo/
COPY db/ ./db/

# Install with all production dependencies
RUN pip install --no-cache-dir -e ".[all]"

# Security: remove build artifacts
RUN rm -rf /root/.cache /tmp/*

# Switch to non-root user
USER citadel

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health/live')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "citadel.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
