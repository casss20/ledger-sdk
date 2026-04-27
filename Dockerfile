# Citadel Governance API
# Production-ready container for the governance kernel
# Multi-stage build: wheel build → runtime

# ── Stage 1: Build the wheel ───────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY apps/runtime/ ./apps/runtime/

# Install build tools and produce a wheel
RUN pip install --no-cache-dir build
RUN python -m build --wheel

# ── Stage 2: Runtime ───────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

# Security: run as non-root
RUN groupadd -r citadel && useradd -r -g citadel citadel

WORKDIR /app

# Copy the wheel from the builder stage
COPY --from=builder /app/dist/*.whl ./

# Copy runtime data files (schema + migrations) needed by the app at startup
COPY db/ ./db/

# Install the wheel with all production extras, then clean up
RUN pip install --no-cache-dir "$(ls *.whl)[all]" && rm *.whl && \
    rm -rf /root/.cache /tmp/*

# Ensure the non-root user can read application files
RUN chown -R citadel:citadel /app

# Switch to non-root user
USER citadel

# Expose API port
EXPOSE 8000

# Health check — readiness endpoint (validates DB connectivity)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health/ready')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "citadel.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
