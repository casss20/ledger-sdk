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
- Redis 7+ for caching
- TLS certificate

---

## Docker Deployment

```bash
docker run -d   --name citadel-sdk   -p 8080:8080   -e CITADEL_API_KEY=ldk_live_...   -e DATABASE_URL=postgres://...   CITADEL/sdk:latest
```

---

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: citadel-sdk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: citadel-sdk
  template:
    metadata:
      labels:
        app: citadel-sdk
    spec:
      containers:
      - name: CITADEL
        image: CITADEL/sdk:latest
        ports:
        - containerPort: 8080
        env:
        - name: CITADEL_API_KEY
          valueFrom:
            secretKeyRef:
              name: CITADEL-secrets
              key: api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: CITADEL-secrets
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
helm repo add CITADEL https://charts.CITADEL.dev
helm install citadel-sdk CITADEL/citadel-sdk   --set apiKey=ldk_live_...   --set database.url=postgres://...
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
