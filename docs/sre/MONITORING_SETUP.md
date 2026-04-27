# SRE Monitoring Stack — Deployment Guide

**Document ID:** SRE-MON-001  
**Version:** 1.0  
**Date:** 2026-04-26  

---

## Overview

Production-ready monitoring stack for Citadel deployments. Covers:

- **Prometheus** — Metrics collection and storage
- **Grafana** — Visualization dashboards
- **Alertmanager** — Alert routing (PagerDuty, Slack, email)
- **Loki** — Log aggregation
- **Jaeger** — Distributed tracing

All components run as Docker Compose services with persistent volumes.

---

## 1. Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Citadel   │────▶│  Prometheus │────▶│   Grafana   │
│    API      │     │  (scrape)   │     │ (dashboard) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │              ┌────┴────┐
       │              ▼         ▼
       │        ┌─────────┐ ┌───────────┐
       │        │ Alertmgr│ │   Loki    │
       │        │(routes) │ │(log agg)  │
       │        └────┬────┘ └─────┬─────┘
       │             │            │
       │             ▼            ▼
       │      ┌─────────┐  ┌─────────┐
       │      │PagerDuty│  │  S3/FS  │
       │      │  Slack  │  │(storage)│
       │      └─────────┘  └─────────┘
       │
       └─────────────────────────────────▶
                                         │
                                    ┌────┴────┐
                                    │ Jaeger  │
                                    │(traces) │
                                    └─────────┘
```

---

## 2. Docker Compose Stack

`docker-compose.monitoring.yml`:

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: citadel-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.4.0
    container_name: citadel-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=${GRAFANA_ROOT_URL:-http://localhost:3000}
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - monitoring
    depends_on:
      - prometheus
      - loki

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: citadel-alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager
    ports:
      - "9093:9093"
    networks:
      - monitoring

  loki:
    image: grafana/loki:2.9.0
    container_name: citadel-loki
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./monitoring/loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    ports:
      - "3100:3100"
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.9.0
    container_name: citadel-promtail
    volumes:
      - /var/log/citadel:/var/log/citadel:ro
      - ./monitoring/promtail-config.yaml:/etc/promtail/config.yml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring
    depends_on:
      - loki

  jaeger:
    image: jaegertracing/all-in-one:1.55
    container_name: citadel-jaeger
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"   # UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: citadel-node-exporter
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:
  alertmanager-data:
  loki-data:

networks:
  monitoring:
    driver: bridge
```

---

## 3. Prometheus Configuration

`monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  # Citadel API
  - job_name: 'citadel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # PostgreSQL (via postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis (via redis_exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

---

## 4. Alerting Rules

`monitoring/rules/citadel-alerts.yml`:

```yaml
groups:
  - name: citadel-slo
    interval: 30s
    rules:
      # Availability SLO: 99.9% over 30 days
      - alert: CitadelHighErrorRate
        expr: |
          (
            sum(rate(citadel_http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(citadel_http_requests_total[5m]))
          ) > 0.001
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Citadel error rate above 0.1%"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
          runbook_url: "https://wiki.internal/citadel/runbooks/high-error-rate"

      # Latency SLO: p99 < 500ms
      - alert: CitadelHighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(citadel_http_request_duration_seconds_bucket[5m])) by (le)
          ) > 0.5
        for: 3m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Citadel p99 latency above 500ms"
          description: "p99 latency is {{ $value }}s"

      # Kill switch activated
      - alert: CitadelKillSwitchActive
        expr: citadel_kill_switch_active > 0
        for: 0s
        labels:
          severity: critical
          team: governance
        annotations:
          summary: "Kill switch is ACTIVE"
          description: "A kill switch has been triggered on {{ $labels.agent_id }}"

      # High policy denial rate
      - alert: CitadelHighDenialRate
        expr: |
          (
            sum(rate(citadel_governance_decisions_total{decision="deny"}[5m]))
            /
            sum(rate(citadel_governance_decisions_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          team: governance
        annotations:
          summary: "High policy denial rate"
          description: "{{ $value | humanizePercentage }} of decisions are denials"

      # Approval queue backing up
      - alert: CitadelApprovalQueueBacklog
        expr: citadel_approval_queue_size > 50
        for: 10m
        labels:
          severity: critical
          team: governance
        annotations:
          summary: "Approval queue has {{ $value }} pending items"

      # Low trust score
      - alert: CitadelLowTrustScore
        expr: citadel_trust_score_avg < 0.5
        for: 15m
        labels:
          severity: warning
          team: security
        annotations:
          summary: "Average trust score below 0.5"

      # Low trust band (PROBATION or REVOKED agents)
      - alert: CitadelLowTrustBand
        expr: citadel_trust_band_standard_count < 0.5
        for: 5m
        labels:
          severity: warning
          team: security
        annotations:
          summary: "Average trust band below STANDARD"

      # Database connection issues
      - alert: CitadelDatabaseUnhealthy
        expr: citadel_db_pool_connections_available < 1
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Database pool exhausted"

      # Agent identity revoked
      - alert: CitadelAgentRevoked
        expr: increase(citadel_agent_identity_revoked_total[1h]) > 0
        for: 0s
        labels:
          severity: warning
          team: security
        annotations:
          summary: "Agent identity revoked"
          description: "{{ $value }} agents revoked in the last hour"
```

---

## 5. Alertmanager Routing

`monitoring/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@citadelsdk.com'
  smtp_auth_username: 'alerts@citadelsdk.com'
  smtp_auth_password: '${SMTP_PASSWORD}'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'team']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
        team: sre
      receiver: 'sre-critical'
      continue: true
    - match:
        severity: critical
        team: governance
      receiver: 'governance-critical'
      continue: true
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#citadel-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  - name: 'sre-critical'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SRE_KEY}'
        severity: critical
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#sre-critical'

  - name: 'governance-critical'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_GOVERNANCE_KEY}'
        severity: critical
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#governance-alerts'

  - name: 'warning'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#citadel-warnings'
```

---

## 6. Deployment

```bash
# 1. Create monitoring directory structure
mkdir -p monitoring/{grafana/{provisioning/{dashboards,datasources},dashboards},rules}

# 2. Set environment
cat > .env.monitoring << 'EOF'
GRAFANA_ADMIN_PASSWORD=changeme-in-production
GRAFANA_ROOT_URL=https://grafana.citadelsdk.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_SRE_KEY=your-sre-service-key
PAGERDUTY_GOVERNANCE_KEY=your-governance-service-key
SMTP_PASSWORD=your-smtp-password
EOF

# 3. Start stack
docker compose -f docker-compose.monitoring.yml --env-file .env.monitoring up -d

# 4. Verify
open http://localhost:9090      # Prometheus
open http://localhost:3000      # Grafana (admin / changeme)
open http://localhost:9093      # Alertmanager
open http://localhost:16686     # Jaeger
```

---

## 7. SLO Definitions

| SLO | Target | Error Budget | Alert Threshold |
|-----|--------|-------------|----------------|
| API Availability | 99.9% | 43m 49s/month | < 99.9% over 5m |
| API Latency p99 | < 500ms | — | > 500ms over 3m |
| API Latency p95 | < 200ms | — | > 200ms over 5m |
| Error Rate | < 0.1% | — | > 0.1% over 2m |
| Governance Decision Latency | < 100ms | — | > 100ms over 5m |
| Policy Evaluation | < 50ms | — | > 50ms over 5m |
| Audit Log Write | < 10ms | — | > 10ms over 1m |
| Database Connection Pool | > 2 available | — | < 2 available |

---

## 8. Grafana Dashboards

Provision dashboards automatically:

`monitoring/grafana/provisioning/dashboards/dashboard.yml`:
```yaml
apiVersion: 1
providers:
  - name: 'citadel-dashboards'
    orgId: 1
    folder: 'Citadel'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

`monitoring/grafana/provisioning/datasources/datasource.yml`:
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
```

---

## 9. Dashboard JSON (Citadel Overview)

Create `monitoring/grafana/dashboards/citadel-overview.json` with these panels:

- **Row 1: System Health**
  - API request rate (QPS)
  - Error rate (%) + threshold line
  - p99 latency (ms)
  - Active connections

- **Row 2: Governance**
  - Decisions per minute (allow/deny)
  - Policy denial rate by agent
  - Approval queue depth
  - Kill switch status (gauge)

- **Row 3: Trust & Identity**
  - Average trust score over time
  - Agent count by trust level
  - Identity verifications/hour
  - Revoked agents count

- **Row 4: Infrastructure**
  - DB connection pool usage
  - CPU / Memory / Disk
  - Container restart count

---

## 10. Cleanup

```bash
docker compose -f docker-compose.monitoring.yml down -v
```

---

**Document Owner:** SRE Team  
**Review Cycle:** Quarterly
