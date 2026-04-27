# Production Deployment Guide

## What you'll learn

- Deploy Citadel SDK to production
- Configure high availability
- Set up monitoring and alerting
- Secure your deployment

---

## Prerequisites

- Kubernetes 1.28+ or Docker
- PostgreSQL 15+ or managed database
- Redis 7+ (optional — see [Redis section](#redis))
- TLS certificate

---

## Docker Deployment

```bash
docker run -d \
  --name citadel \
  -p 8000:8000 \
  -e CITADEL_API_KEYS=prod-key-1:admin \
  -e CITADEL_DATABASE_URL=postgresql://user:pass@host:5432/citadel \
  -e CITADEL_JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  citadel-runtime:latest
```

---

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: citadel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: citadel
  template:
    metadata:
      labels:
        app: citadel
    spec:
      containers:
      - name: citadel
        image: citadel-runtime:latest
        ports:
        - containerPort: 8000
        env:
        - name: CITADEL_API_KEYS
          valueFrom:
            secretKeyRef:
              name: citadel-secrets
              key: api-keys
        - name: CITADEL_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: citadel-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Redis (Optional)

Redis is **not required** for single-node deployments. It becomes necessary when running multiple API instances that need shared state.

### Without Redis (single-node)

| Feature | Behavior |
|---|---|
| Rate limiting | In-memory token bucket per instance |
| Kill switch | In-memory per instance |
| Caching | In-memory dict per process |

### With Redis (multi-node)

| Feature | Behavior |
|---|---|
| Rate limiting | Distributed token bucket across all instances |
| Kill switch | Shared state (planned) |
| Caching | Shared cache across instances |

To enable Redis, set `CITADEL_REDIS_URL=redis://host:6379/0` in your environment and uncomment the `redis` service in `docker-compose.yml`.

---

## Helm Chart

> **Helm Chart**: A Helm chart is planned but not yet published. Track progress at https://github.com/casss20/citadel-sdk/issues.

---

## High Availability

- Run 3+ replicas across availability zones
- Use managed PostgreSQL with replication
- Configure Redis Sentinel for cache HA (if using Redis)
- Enable automatic failover

---

## Monitoring

### Health checks
```
GET /v1/health/live   # Liveness probe
GET /v1/health/ready  # Readiness probe
GET /metrics          # Prometheus metrics
```

### Key metrics
| Metric | Alert Threshold |
|--------|----------------|
| `CITADEL_policy_eval_latency` | p99 > 10ms |
| `CITADEL_audit_ingest_rate` | < 1000/sec |
| `CITADEL_kill_switch_active` | > 0 |

---

## Security

- Use dedicated API keys per environment
- Enable IP allowlisting
- Configure audit event forwarding to SIEM
- Rotate secrets every 90 days
- Enable MFA for dashboard access

---

## Next steps

- [Monitoring Governance](monitoring-governance.md)
- [Security Best Practices](security-best-practices.md)
- [Scaling to Millions of Agents](scaling-to-millions-of-agents.md)
