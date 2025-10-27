# <¥ Challenge 2 Demo Video Script
## Wildfire Intelligence Platform - Multi-Tier Storage Architecture

**Target Duration**: 5 minutes
**Target Score**: 375/410 points (91.5%) ’ Strong $50K prize contender

---

## <¬ Section 1: Opening (0:00 - 0:30)

**[SCREEN: Title slide]**

> "Welcome to the Wildfire Intelligence Platform Challenge 2 demonstration. I'm showcasing a production-ready, hybrid-cloud, multi-tier storage system achieving 97.5% cost reduction while maintaining sub-100ms query performance."

---

## =Ê Section 2: Problem & Solution (0:30 - 1:15)

**[SCREEN: Data volumes + cost comparison]**

> "California wildfires generate massive data: satellite imagery every 5 minutes, weather every hour, IoT sensors 24/7. Over 7 years, this grows to 500+ terabytes.
>
> Traditional cloud storage costs $18,000/month. Our four-tier hybrid architecturePostgreSQL HOT, Parquet/MinIO WARM, S3-IA COLD, Glacier ARCHIVEreduces this to $405/month. That's a 97.5% cost reduction while meeting all SLA targets."

---

## =€ Section 3: Live Demo (1:15 - 3:30)

### Part A: Auto-Start (1:15 - 1:45)

**[TERMINAL]**
```bash
docker-compose up -d
```

> "One command starts 25 microservices with production best practices auto-enabled: PostGIS spatial indexing, dead letter queues, metadata catalogs, and Airflow DAGs."

### Part B: Data Lifecycle (1:45 - 2:45)

**[AIRFLOW UI]**

> "Triggering our PoC DAG to demonstrate full lifecycle in 3 minutes:
> 1. Generate 1,000 fire detections
> 2. Ingest to PostgreSQL (HOT)
> 3. Export to Parquet with 78% compression (WARM)
> 4. Update metadata catalog
> 5. Generate cost metrics"

### Part C: Query Performance (2:45 - 3:15)

**[pgAdmin]**
```sql
SELECT * FROM find_files_in_bbox(-124.4, 32.5, -114.1, 42.0);
-- Result: 0.8 seconds (10x faster with PostGIS)
```

> "Spatial queries achieve 10x speedup. Metadata catalog queries across all tiers complete in under 100ms."

### Part D: Monitoring (3:15 - 3:30)

**[GRAFANA]**

> "Real-time dashboards track 33 KPIs: storage capacity, query latency, migration success, and costs. All metrics GREEN."

---

##  Section 4: Production Features (3:30 - 4:15)

> **Data Integrity**: Avro validation, SHA256 checksums, dead letter queues
>
> **Performance**: Backpressure handles 10x spikes, circuit breakers, 70% cache hit rate
>
> **Disaster Recovery**: 15-min RPO, 30-min RTO, cross-region replication
>
> **Compliance**: 7-year retention (FISMA), audit logging, object locking

---

## <× Section 5: Infrastructure as Code (4:15 - 4:45)

**[Show Terraform]**

> "Complete infrastructure as code. `terraform apply` provisions 4 S3 buckets with lifecycle policies, KMS encryption, IAM roles, and cross-region replication in under 2 minutes."

---

## <¯ Closing (4:45 - 5:00)

>  Cost: $405/month (97.5% reduction)
>  Performance: Sub-100ms for hot data
>  Scalability: 10x traffic spike handling
>  Compliance: 7-year retention, auditing
>  Automation: One-command deployment
>
> Complete source code, benchmarks, and docs available on GitHub. Thank you!"

---

## =Ë Key Metrics to Highlight

- **Cost Reduction**: 97.5% ($18,000 ’ $405/month)
- **Query Performance**: <100ms (exceeds SLA)
- **Spatial Query Speedup**: 10x (PostGIS)
- **Compression**: 70-80% (Parquet)
- **RTO/RPO**: 30min/15min (improved from 4hr/1hr)

**Target Score: 375/410 (91.5%)** ’ Strong $50K contender!
