# Production Deployment Guide

## What you'll learn

- Deploy Ledger SDK to production
- Configure high availability
- Set up monitoring and alerting
- Secure your deployment

---

## Prerequisites

- Kubernetes 1.28+ or Docker
- PostgreSQL 15+ or managed database
- Redis 7+ for caching
- TLS certificate

---

## Docker Deployment

```bash
docker run -d   --name ledger-sdk   -p 8080:8080   -e LEDGER_API_KEY=ldk_live_...   -e DATABASE_URL=postgres://...   ledger/sdk:latest
```

---

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ledger-sdk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ledger-sdk
  template:
    metadata:
      labels:
        app: ledger-sdk
    spec:
      containers:
      - name: ledger
        image: ledger/sdk:latest
        ports:
        - containerPort: 8080
        env:
        - name: LEDGER_API_KEY
          valueFrom:
            secretKeyRef:
              name: ledger-secrets
              key: api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: ledger-secrets
              key: database-url
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Helm Chart

```bash
helm repo add ledger https://charts.ledger.dev
helm install ledger-sdk ledger/ledger-sdk   --set apiKey=ldk_live_...   --set database.url=postgres://...
```

---

## High Availability

- Run 3+ replicas across availability zones
- Use managed PostgreSQL with replication
- Configure Redis Sentinel for cache HA
- Enable automatic failover

---

## Monitoring

### Health checks
```
GET /healthz     # Liveness probe
GET /readyz      # Readiness probe
GET /metrics     # Prometheus metrics
```

### Key metrics
| Metric | Alert Threshold |
|--------|----------------|
| `ledger_policy_eval_latency` | p99 > 10ms |
| `ledger_audit_ingest_rate` | < 1000/sec |
| `ledger_kill_switch_active` | > 0 |

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
