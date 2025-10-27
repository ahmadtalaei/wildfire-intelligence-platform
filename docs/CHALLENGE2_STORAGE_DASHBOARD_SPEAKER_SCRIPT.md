
Welcome to the Challenge Two Storage Tier Monitoring Dashboard… a comprehensive real-time monitoring system tracking hybrid storage infrastructure across four storage tiers.

Before we begin… ensure your Docker Compose environment is running… as this dashboard displays live monitoring of actual data storage operations.


## Accessing the Dashboard

Open your web browser and navigate to localhost port three thousand ten.

You will see the Grafana login page.

Enter the username… admin… all lowercase.

Then the password… also admin… all lowercase.

Click Sign In to access the Grafana dashboard interface.


Once logged in… you have two options to view the Challenge Two Storage Tier Monitoring Dashboard.

Option one… if the dashboard is already imported… simply click on Dashboards in the left sidebar.

Then search for Challenge Two Storage… or scroll through the list to find it.

Click on the dashboard name to open it.


Option two… if you need to import the dashboard from the JSON file.

Click the plus icon in the left sidebar… then select Import dashboard.

Click Upload JSON file… and browse to the file location.

Navigate to monitoring slash grafana slash dashboards slash challenge two storage dashboard json file.

Select the file and click Import.

If the dashboard is already imported… Grafana may display an error stating… A dashboard or folder with the same name already exists.

Once imported successfully… Grafana will load the dashboard configuration… and you will see the Challenge Two Storage Tier Monitoring Dashboard appear.


Please note... that the metrics shown reflect recent ingestion and consumption activity... Since the Docker environment was just started for this recording, some panels, especially time-series charts—may temporarily display no data... 

The dashboard provides near real-time visibility into storage performance… capacity… costs… security… and compliance.

It refreshes automatically every thirty seconds… so within a few refresh cycles… all panels will populate with real-time data from the continuous monitoring service.



## Query Performance Monitoring

At the top of the dashboard… four performance gauges track query latency across all storage tiers and overall service level agreement compliance.

The first three gauges monitor HOT tier… WARM tier… and COLD tier query latency at the ninety-fifth percentile.

HOT tier uses PostgreSQL on NVMe solid-state drives for sub-one hundred millisecond queries.

WARM tier uses Parquet files on MinIO object storage with a five hundred millisecond service level agreement.

COLD tier retrieves from Amazon S3 Standard Infrequent Access with a five-second target.

The fourth gauge aggregates all performance metrics… backup success rates… and replication lag into an overall service level agreement compliance score.

These gauges demonstrate that our hybrid storage architecture meets Challenge Two requirements for performance optimization across tiered storage.


## Storage Capacity Management

The second row displays four capacity gauges showing utilization across all tiers.

HOT tier capacity is fifty terabytes of NVMe solid-state drives… holding the most recent seven days of data.

WARM tier provides two hundred terabytes of hard disk drives… storing data from day seven to day ninety.

COLD tier offers five petabytes on Amazon S3 Standard Infrequent Access… holding data from ninety days to one year.

ARCHIVE tier delivers one hundred petabytes on S3 Glacier Deep Archive… providing seven-year retention for FISMA compliance.

These gauges monitor capacity thresholds… alerting operations teams before storage limits are reached… addressing Challenge Two requirements for scalable storage infrastructure.


## Storage Distribution Analysis

The third row presents two complementary views of data distribution.

The pie chart on the left shows proportional storage by tier… color-coded for quick visual identification.

The table on the right displays exact storage sizes for each tier in a grid format with visible borders.

Together… these panels provide both quantitative and qualitative understanding of how data distributes across the tiered architecture… validating the storage lifecycle strategy.


## Comprehensive Storage Tier Breakdown

The full-width table below provides complete operational details for all storage tiers in a single view.

Six columns display Tier… Files… Total Size… Storage Type… Retention… and Cost per Gigabyte.

HOT tier shows PostgreSQL on NVMe solid-state drives with zero to seven day retention.

WARM tier displays MinIO Parquet on hard disk drives with seven to ninety day retention.

COLD tier indicates S3 Standard Infrequent Access with ninety to three hundred sixty-five day retention.

ARCHIVE tier presents Glacier Deep Archive with three hundred sixty-five plus day retention and seven-year compliance policy.

The cost column demonstrates the ninety-seven point five percent cost reduction from HOT to ARCHIVE tier… proving Challenge Two cost optimization deliverables.

This table is the primary reference for understanding storage architecture… retention policies… and cost efficiency at a glance.


## Data Lifecycle Migration Activity

Below the comprehensive table… three stat panels track automated migration activity in the last twenty-four hours.

The first panel monitors Hot to Warm migrations… showing files aged beyond seven days transitioning to MinIO storage.

The second panel tracks Warm to Cold migrations… displaying files aged beyond ninety days moving to S3 Standard Infrequent Access.

The third panel shows Cold to Archive migrations… indicating files exceeding one year transitioning to Glacier Deep Archive.

These panels validate that Apache Airflow orchestration is executing lifecycle policies correctly… ensuring data ages through tiers without manual intervention… addressing Challenge Two automation requirements.


## Cost Analysis and Migration Queue Monitoring

The next row displays a large timeseries chart tracking storage costs over time and a gauge monitoring migration queue depth.

The cost chart shows four lines representing each tier's monthly cost estimate based on data volume and tier-specific pricing.

This visualization helps finance teams forecast cloud spending and validate cost optimization strategies.

The migration queue depth gauge monitors files waiting to migrate to the next tier.

Rising queue depth indicates migration jobs are falling behind data aging… requiring investigation into Airflow scheduler performance or resource constraints.

These panels demonstrate Challenge Two cost optimization and operational efficiency deliverables.


## Backup Success and Replication Monitoring

Three panels track backup operations… database replication… and data ingestion rates.

The first gauge shows backup success rate over the last twenty-four hours… tracking Veeam backup jobs across all storage tiers.

The second gauge displays PostgreSQL replication lag in seconds… measuring the delay between primary and standby databases.

Replication lag under the service level agreement threshold ensures minimal data loss during failover events.

The third panel shows data ingestion rate as a timeseries chart… displaying events per second flowing into the storage pipeline.

These metrics validate Challenge Two requirements for data durability… disaster recovery… and high availability.


## Security and Compliance Monitoring

Four stat panels track security events and compliance metrics.

The first panel monitors failed authentication attempts in the last hour… detecting potential brute-force attacks or compromised credentials.

The second panel displays API rate limit violations… identifying misconfigured clients or denial-of-service attempts.

The third panel shows compliance rule violations… tracking encryption enforcement… retention policy adherence… and access controls.

Zero compliance violations confirms the system maintains FISMA compliance and NIST eight hundred fifty-three control requirements.

The fourth panel monitors encryption key rotation status… showing days since the last AWS Key Management Service rotation.

Regular key rotation reduces the impact of potential key compromise… addressing Challenge Two security and governance deliverables.


## Cost Optimization Metrics

Two large stat panels track overall cost efficiency.

The first panel displays blended cost per gigabyte across all storage tiers… calculating the weighted average based on data distribution.

This metric demonstrates the cost efficiency of the tiered storage strategy compared to single-tier storage.

The second panel shows monthly spend variance versus budget… indicating whether actual costs are above or below forecasted spending.

Negative variance indicates cost savings… while positive variance triggers budget reviews.

These panels prove Challenge Two cost optimization deliverables… showing that hybrid storage achieves significant cost reduction while maintaining performance.


## Data Quality and Compliance Tracking

Two panels monitor data quality and storage compliance over time.

The quality score chart displays a timeseries tracking schema validation… field completeness… data consistency… and anomaly detection.

Quality scores above the target threshold ensure data integrity throughout the storage pipeline.

The storage tier compliance gauge shows the percentage of files properly assigned to valid storage tiers.

This metric confirms no files are orphaned… mislabeled… or stuck in the wrong tier… validating lifecycle management effectiveness.

These panels address Challenge Two data governance and quality assurance deliverables.


## Historical File Statistics

Three panels at the bottom show historical trends.

The files created over time chart displays daily file creation rates… helping capacity planners forecast storage growth.

The files by compression type pie chart shows the distribution between compressed and uncompressed data.

Most files use Snappy compression in the WARM tier… achieving significant storage savings.

The files by format pie chart displays the split between Parquet and PostgreSQL formats.

Parquet dominates because most data eventually ages into the WARM… COLD… and ARCHIVE tiers where this format is used.

These panels provide historical context for understanding storage growth patterns and compression effectiveness.


## Data Flow Through the Storage Pipeline

Understanding how data flows through the storage architecture is critical.

When a satellite detects a fire… data flows through Apache Kafka… validated against Avro schemas… and inserted into the PostgreSQL HOT tier.

After seven days… Apache Airflow triggers the hot-to-warm migration… exporting data to Parquet format with Snappy compression and storing on MinIO.

After ninety days… Airflow triggers the warm-to-cold migration… uploading Parquet files to Amazon S3 Standard Infrequent Access.

After one year… Airflow triggers the cold-to-archive migration… transitioning files to S3 Glacier Deep Archive for seven-year retention.

Throughout this lifecycle… the dashboard monitors query latency… migration success… backup completion… security events… and costs… ensuring smooth operations at every stage.


## Challenge Two Deliverables Demonstrated

This dashboard directly addresses multiple Challenge Two deliverables.

The architecture and design deliverables are proven through the four-tier hybrid storage model… combining on-premises PostgreSQL and MinIO with cloud-based S3 storage.

Governance and security deliverables are validated through compliance monitoring… encryption tracking… audit logging… and access control metrics.

Performance and operational readiness deliverables are demonstrated through service level agreement tracking… capacity monitoring… and cost optimization metrics.

The dashboard shows real-time proof that the storage architecture meets latency targets… maintains data integrity… enforces security policies… and achieves cost efficiency.


## Operational Value

This dashboard transforms storage metrics into actionable intelligence for operations teams.

It ensures service level agreements are met across all tiers… guaranteeing fire chiefs can query recent data with sub-one hundred millisecond latency.

It validates cost optimization… confirming the tiered strategy delivers significant savings compared to single-tier storage.

It monitors security and compliance… ensuring the platform meets government standards for data protection.

It tracks data quality and lifecycle management… ensuring no data is lost during migrations.

It provides capacity planning visibility… alerting when tiers approach limits.

Operations teams use this dashboard to proactively identify issues before they impact fire response… representing the future of cloud-native storage operations with real-time visibility… automated lifecycle management… and continuous cost optimization.
