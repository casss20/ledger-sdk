# Scaling to Millions of Agents

## What you'll learn

- Architect for massive scale
- Shard agents across regions
- Optimize policy evaluation
- Handle high-throughput audit ingestion

---

## Architecture

```
Load Balancer
    ↓
Citadel API (auto-scaled)
    ↓
Policy Cache (Redis Cluster)
    ↓
Audit Ingest (Kafka → S3)
    ↓
Search Index (Elasticsearch)
```

---

## Policy Evaluation Optimization

- Cache compiled policies in Redis (TTL: 5 minutes)
- Use policy sharding by agent namespace
- Batch evaluate similar actions
- Pre-compute condition results

Performance:
- p99 latency: <5ms with caching
- Throughput: 100,000 decisions/second per shard

---

## Audit Ingestion

- Use Kafka for buffering
- Batch write to S3 (1000 records/batch)
- Async indexing to Elasticsearch
- Handle 1M events/second with 3 shards

---

## Regional Deployment

```yaml
regions:
  - name: us-east
    replicas: 5
    database: postgres-us-east
  - name: eu-west
    replicas: 5
    database: postgres-eu-west
  - name: ap-south
    replicas: 3
    database: postgres-ap-south
```

Cross-region replication for audit trail:
- Write to local region
- Replicate to 2 other regions asynchronously
- RPO: <1 minute

---

## Next steps

- [Production Deployment](production-deployment.md)
