# Citadel Runtime Backend Setup

The `citadel-kernel` SDK requires a running Citadel runtime backend. This guide covers local setup for development and testing.

## Quick Start (Docker)

```bash
# From repository root
docker build -f apps/runtime/Dockerfile -t citadel-runtime .
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite:///citadel.db" \
  -e CITADEL_MODE="local_dev" \
  citadel-runtime
```

Backend is now available at `http://localhost:8000`.

## Local Development (Python)

```bash
# Install runtime dependencies
cd apps/runtime
pip install -e .

# Run migrations to initialize database
python -m alembic upgrade head

# Start the runtime server
python -m uvicorn citadel.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Environment variables:
- `DATABASE_URL` — SQLite (default: `sqlite:///citadel.db`) or PostgreSQL connection string
- `CITADEL_API_KEY` — API key for backend auth (generate a random string for local dev)
- `CITADEL_MODE` — `local_dev`, `staging`, or `production`

## Database Setup

SQLite (development):
```bash
cd apps/runtime
sqlite3 citadel.db < /dev/null  # Creates empty DB
python -m alembic upgrade head
```

PostgreSQL (production-like):
```bash
# Ensure PostgreSQL is running
createdb citadel
export DATABASE_URL="postgresql://user:password@localhost/citadel"
cd apps/runtime
python -m alembic upgrade head
```

## Testing the Backend

Once running, verify health:

```bash
curl http://localhost:8000/v1/health
# Should return: {"status": "ok", "version": "0.1.0"}
```

## Using with citadel-kernel SDK

Point the SDK to your backend:

```python
import citadel_kernel as ck

client = ck.KernelClient(
    base_url="http://localhost:8000",
    api_key="your_local_key_here",  # Match CITADEL_API_KEY env var
    actor_id="local-agent",
)

# Now execute() and other methods will hit your local backend
result = await client.execute(
    action="llm.generate",
    provider="anthropic",
    model="claude-opus-4-7",
    input_tokens=1000,
    output_tokens=500,
)
```

## Troubleshooting

**"Connection refused"**: Backend not running. Check Docker container or Python server is alive.

**"Authentication failed"**: SDK api_key doesn't match backend CITADEL_API_KEY env var.

**"Database locked"**: SQLite contention. Use PostgreSQL for concurrent testing.

**Missing tables**: Run `python -m alembic upgrade head` to apply migrations.

## Production Deployment

For production, use PostgreSQL and configure:
- `CITADEL_MODE=production`
- Reverse proxy (nginx) for TLS
- Environment variable secrets management
- Monitor logs and uptime

See `apps/runtime/README.md` for full deployment guide.
