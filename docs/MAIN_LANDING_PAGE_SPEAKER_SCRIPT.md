

Welcome to the Wildfire Intelligence Platform… a comprehensive, competition-ready solution for the CAL FIRE Space-Based Data Acquisition, Storage, and Dissemination Challenge.

This platform demonstrates a complete end-to-end system… addressing all three competition challenges through integrated microservices… hybrid cloud storage architecture… and advanced analytics capabilities.

Before we begin… ensure your Docker Compose environment is running… as this dashboard displays live metrics from actual running services and real-time data streams.



Open your web browser and navigate to localhost port three thousand.

You will see the Wildfire Intelligence Platform landing page… featuring a purple gradient background with white text… displaying all available platform services and interfaces.



At the top of the dashboard… just below the header… you'll see the Real-Time Data Monitoring section.

This section displays four demo metric cards… 



The first card… highlighted in red… shows Fire Incidents.

The large number displays the count of active wildfire detections from NASA FIRMS satellites at the time.


Next to it… the blue card displays Weather Data.

This metric shows the number of recent weather station readings processed by the platform.

Weather data flows from NOAA weather stations… aviation weather systems… and climate reanalysis models.



The third card… tracks Sensor Data.

This number represents readings from hundreds of IoT air quality sensors and weather stations across California.

Our platform integrates with PurpleAir sensors… providing real-time particulate matter measurements that indicate smoke presence and air quality degradation.


The fourth card… shows Data Ingestion status.

The text displays either Healthy or the number of records processed recently.


Below the metric cards… three interactive buttons provide quick access to platform features.

The red View Recent Fires button opens a detailed table showing the latest wildfire detections… including coordinates… brightness temperature… confidence scores… and detection timestamps.

The green System Health button executes a comprehensive health check… querying all microservices to verify they're responding correctly… reporting service status… response times… and any connectivity issues.

The API Docs button opens interactive Swagger documentation… where developers can browse all REST API endpoints… test them interactively… view request and response schemas… and download the OpenAPI specification.

These buttons demonstrate operational readiness… allowing real-time system validation during the presentation.



Moving down the page… you'll see a grid of service cards… each representing a key platform component.

Each card includes a green pulsing status indicator… service description… and action buttons for accessing that service.

Let's explore each service systematically.


The first card… displays System Architecture.

This represents the complete eight-layer end-to-end architecture integrating all three competition challenges.




The card offers three ways to explore the architecture.

Click Diagram to view the static Mermaid visualization… showing all eight layers with detailed component listings… data flow arrows… and technology stack annotations.

The architecture spans from user-facing presentation layers at the top… through API gateways and orchestration in the middle… down to data storage and infrastructure layers at the bottom.


The Live Dynamic View button… notice it's pulsing with a pink-to-red gradient… opens an interactive real-time architecture diagram.

In this demo view… you can watch data flowing through the system… see service health status changing… and observe connections between components updating in real-time.

The Quick Summary button displays a concise text overview… listing key technologies… major components… and architectural decisions… perfect for executive summaries.

This architecture documentation directly addresses Challenge One's requirement for architectural blueprints… Challenge Two's hybrid storage design… and Challenge Three's platform interface deliverables.

We have a separate detailed session covering the architecture… so we'll proceed to the next service.



The second card shows the Data Storage Service… the backbone of Challenge Two.

This service manages our hybrid storage strategy across four distinct tiers.

The HOT tier… running on PostgreSQL with TimescaleDB… handles queries requiring sub-one hundred millisecond response times… storing the most recent seven days of data.

The WARM tier… using Parquet files on MinIO object storage… serves analytical queries with sub-five hundred millisecond latency… holding data from seven to ninety days old.

The COLD tier… leveraging AWS S3 Standard Infrequent Access… supports compliance queries with sub-five second response times… archiving data from ninety to three hundred sixty-five days.

The ARCHIVE tier… using S3 Glacier Deep Archive… provides seven-year retention for regulatory compliance… with twelve-hour retrieval times.

The Health button checks service status… verifying database connections… storage tier availability… and migration job execution.

API Docs opens the complete REST API documentation... showing endpoints for data upload… retrieval… tier migration… and metadata management.

This tiered architecture achieves significant cost reduction compared to traditional hot storage… storing ten terabytes for four hundred five dollars per month instead of eighteen thousand dollars.


The third card represents PostgreSQL Database… our primary relational database.

PostgreSQL stores structured metadata… user accounts… system configuration… audit logs… and spatial data with PostGIS extensions.

TimescaleDB extensions enable high-performance time-series queries… automatically partitioning tables by time… compressing old data… and maintaining hypertables for fire detection and sensor reading datasets.

The pgAdmin Connection button opens pgAdmin web interface at port five thousand fifty… providing graphical database management… query execution… schema visualization… and performance monitoring.



Let's demonstrate live data ingestion by accessing the database directly.

Click the Connection button to open pgAdmin at localhost port five thousand fifty.

You'll see the pgAdmin login page.

Enter the email address… admin at wildfire dot gov.

Enter the password… admin one two three.

Click Login to access the database management interface.


In the left sidebar… you'll see the server browser tree.

Right-click on Servers… and select Register… then Server.

In the General tab… enter a name… such as Wildfire PostgreSQL.

Click the Connection tab.

Enter the hostname… postgres … or if that doesn't work… try localhost.

Enter the port… five four three two.

Enter the maintenance database… wildfire_db.

Enter the username… wildfire_user.

Enter the password… wildfire_password.

Click the Save password checkbox to avoid re-entering it.

Click Save to register the server connection.


The server will connect and display the database tree in the left sidebar.

Expand Servers… then expand Wildfire PostgreSQL.

Expand Databases… then expand wildfire underscore db.

Expand Schemas… then expand public.

You'll see a list of tables stored in the database.


Locate the table named noaa underscore station underscore observations.

This table stores real-time weather station data continuously ingested from NOAA.

Right-click on noaa underscore station underscore observations.

Select Query Tool to open the SQL editor.


In the query editor window… type the following SQL command…

...

And run the query.

The results panel below will display the count… showing the total number of weather observations currently stored.

Note this number…


Now… wait about thirty seconds… allowing the data ingestion service to fetch and store new weather observations.

To view the actual data… let's type a new query…


Run this query...

The results panel displays one hundred rows of weather observation data… showing columns like station ID… temperature… humidity… wind speed… pressure… and observation timestamp...


Let's Re-run the same count query...

The count have increased… This demonstrates live data ingestion… with new weather observations flowing into the database continuously… validating our Challenge One real-time data pipeline...


This confirms storing real-time data… demonstrating our end-to-end data flow from external datasources… through the ingestion service… into PostgreSQL storage.


Going back to main platform, the Connection Info displays database credentials… connection parameters… and current performance metrics including database size… active connections… connection pool utilization… and query performance statistics.

This database directly supports Challenge Three's metadata catalog deliverable… storing dataset descriptions… lineage information… quality scores… and access statistics.



Next we have Redis Cache… our high-performance in-memory data store.

Redis accelerates the platform by caching frequently accessed query results… reducing database load and improving response times.

It stores user sessions… enabling fast authentication checks without database queries for every request.

It buffers real-time data streams… temporarily holding incoming sensor readings before batch insertion into PostgreSQL.

It manages rate limiting counters… tracking API request quotas per user and preventing abuse.

Since Redis operates via command-line interface… the Connection button explains how to connect using redis-cli… Docker exec commands… or desktop tools like RedisInsight.

Connection Info shows connection details… current memory usage… connected client count… total keys stored… and cache hit rate percentage.




The MinIO card represents our S3-compatible object storage for large binary files.

MinIO stores satellite imagery from Landsat and Sentinel satellites… each image ranging from five to twenty megabytes.

It holds trained machine learning models… including random forest classifiers for fire risk prediction… neural networks for smoke detection… and regression models for fire spread simulation.

It archives historical datasets… such as complete fire season perimeters… multi-year weather records… and vegetation index time series...

The Connection button opens the MinIO web interface at port nine thousand one… where you can browse buckets… upload and download files… set access policies… and monitor storage usage.

Connection Info displays access key and secret key credentials… API endpoint URLs… bucket configurations… and storage metrics including total objects… storage consumption… and data transfer rates.

MinIO serves as the WARM tier storage backend… demonstrating Challenge Two's hybrid storage implementation with S3-compatible APIs enabling seamless cloud migration.





Moving to the next row… the Data Ingestion Service card showcases Challenge One's core deliverable.

This service continuously pulls data from twelve external sources… each with different protocols… formats… and update frequencies.

NASA FIRMS provides satellite fire detections every fifteen minutes via REST API… using Avro schema validation to ensure data quality.

NOAA weather stations stream atmospheric conditions via JSON… including temperature… humidity… wind speed… and barometric pressure.

Copernicus Sentinel satellites supply multispectral imagery via WMS services… delivering vegetation indices and thermal anomaly detection.

PurpleAir IoT sensors publish air quality measurements every sixty seconds via MQTT… tracking particulate matter concentrations indicating smoke presence.

The service validates all incoming data against predefined schemas… rejecting malformed records… logging validation failures to a dead letter queue… and tracking data quality scores per source.

Validated data publishes to Kafka topics… enabling real-time stream processing… decoupling ingestion from consumption… and supporting multiple downstream consumers.

The Health button verifies if all the data connectors are operational… showing last successful fetch timestamp… error rates… and connection status for each source.

API Docs reveals the ingestion REST API at port eight thousand three… with endpoints for triggering manual fetches… viewing connector status… replaying failed records… and configuring polling intervals.

This service directly addresses Challenge One's data ingestion prototype deliverable… demonstrating source adapters for batch and streaming data… support for multiple formats including JSON… CSV… GeoJSON… and binary imagery… and scalable pipeline architecture using Kafka message queues.





The Metrics Monitoring Service card tracks Challenge One's latency and fidelity requirements.

This service collects over fifty performance indicators across the data pipeline.

Latency metrics measure end-to-end ingestion time from external source to Kafka publication… per-connector processing time… queue depth and consumer lag… and throughput rates in events per second.

Fidelity metrics track Avro schema validation pass rates… data quality scores based on completeness and consistency… field-level validation results… and anomaly detection findings.

The service exports all metrics to Prometheus… a time-series metrics database… enabling historical trend analysis… alerting on threshold violations… and capacity planning.

Health confirms the monitoring service is collecting metrics… showing last collection timestamp and metric count.

API Docs opens the metrics REST API… providing programmatic access to current and historical metrics.

Metrics Dashboard launches the Grafana visualization at port three thousand ten… displaying real-time charts… time-series graphs… and statistical distributions.

We have dedicated sessions covering the Metrics Dashboard… the Storage Tier Monitoring Dashboard… and the Data Clearing House & Analytics Dashboard… so we'll note their availability and continue.

Login Info provides Grafana credentials… username admin… password admin… for accessing all monitoring dashboards.

This comprehensive monitoring validates Challenge One's requirement for latency visualization… fidelity checks… and performance tracking dashboards.





The Storage Tier Monitoring card showcases Challenge Two's infrastructure observability.

This Grafana dashboard tracks thirty-three key performance indicators across all four storage tiers.

This monitoring directly supports performance and operational readiness deliverables… with scalability demonstrated through load simulation metrics… redundancy validated through backup success rates… and cost optimization proven through expenditure tracking.





The Data Clearing House and Analytics Platform card represents Challenge Three's comprehensive deliverable.

This is a complete analytics ecosystem… not just a single service… but an integrated platform spanning multiple components.

The Data Clearing House at port eight thousand six provides a self-service data portal… allowing users to discover datasets through a searchable catalog… build queries using a visual query builder or SQL editor… execute queries with sub-two hundred millisecond response times… and export results in CSV… JSON… GeoJSON… Parquet… or Excel formats.

The platform offers forty-five REST API endpoints… covering dataset listing… metadata retrieval… query execution… result pagination… export generation… and usage tracking...

API Docs shows the complete REST API… enabling programmatic access for automated workflows… integration with business intelligence tools… and custom application development...


The Analytics Dashboard… hosted in Grafana at port three thousand ten… monitors real-time user activity… query performance metrics… role-based analytics showing different usage patterns for each user persona… session tracking… and live export monitoring.

The platform supports five user roles… Fire Chief for operational decision-making… Data Analyst for statistical reporting… Data Scientist for machine learning research… Admin for system management… and Field Responder for mobile incident access.

Each role has customized dashboards… tailored data access permissions… specific query templates… and role-appropriate visualizations.


The platform and dashboard directly addresses Challenge Three deliverables across all categories… Platform and Interface deliverables through role-specific dashboards… Security and Governance through access control and audit logging… and Backend and Processing through query optimization and multi-format exports.

We have a separate session dedicated to the Data Clearing House and Analytics Platform… so we'll continue to the user-facing dashboards.





The Fire Chief Dashboard card represents one of the five role-based interfaces.

Open Dashboard launches the Fire Chief interface… where you can explore the interactive map… view incident details… and access operational tools.

This React-based dashboard at port three thousand one provides operational intelligence for incident commanders.

The interface displays real-time wildfire maps with satellite imagery overlays… weather pattern visualizations… and smoke dispersion modeling.

It tracks active incidents with status updates… containment percentages… acres burned… and resource assignments.

It shows resource deployment status… indicating available firefighting crews… air tankers… bulldozers… and helicopter positions.

It provides incident command tools… enabling chiefs to request additional resources… update incident status… and communicate with field teams...


Operations Monitor links to additional Grafana dashboards tracking operational metrics… response times… resource utilization… and incident outcomes...

We have a dedicated session covering the Fire Chief Dashboard in detail… so we'll note its availability for separate exploration...





The Data Scientist Workbench card provides scientific computing capabilities.

This interface at port three thousand three serves researchers developing predictive models and analyzing fire patterns.

Scientists access raw datasets… including unprocessed satellite imagery… complete weather station time series… and full-resolution sensor readings.

They train machine learning models… using scikit-learn for classification… TensorFlow for deep learning… and PyTorch for custom neural architectures.

They run Jupyter notebooks… conducting exploratory analysis… visualizing data distributions… and documenting research findings.

They perform geospatial analysis… calculating vegetation indices… analyzing topographic influences… and modeling fire spread patterns.

Open Workbench launches the scientist interface… providing access to all analytical tools and datasets.

This interface will be covered in a separate detailed session… so we'll continue forward.

Login Info displays credentials… username scientist at calfire dot gov… password admin.





The Data Analyst Portal card supports business intelligence and reporting workflows.

This interface at port three thousand two enables analysts to produce executive briefings and statistical summaries.

Analysts generate statistical reports… calculating fire frequency by region… seasonal trend analysis… resource deployment efficiency… and incident outcome metrics.

They visualize trends over time… creating line charts showing acres burned per month… bar charts comparing response times across counties… and heatmaps displaying high-risk areas.

They create custom charts… selecting data series… configuring axes… applying filters… and exporting publication-ready graphics.

They export findings… downloading reports as PDFs… charts as PNG images… and data tables as Excel spreadsheets for stakeholder distribution.

Open Portal launches the analyst interface… where you can explore reporting capabilities and visualization tools.

We have a separate session covering the Data Analyst Portal… so we'll note it and proceed.

Login Info shows credentials… username analyst at calfire dot gov… password admin.




The Admin Console card provides system administration capabilities.

This interface at port three thousand four handles platform governance and configuration.

Admins manage user accounts… creating new users… assigning roles… resetting passwords… and deactivating accounts for departed staff.

They configure system settings… adjusting data retention policies… setting backup schedules… defining alert thresholds… and customizing dashboard layouts.

They monitor audit logs… reviewing user activity… tracking data access… identifying security events… and generating compliance reports...

They oversee platform security… managing encryption keys… configuring firewall rules… reviewing failed login attempts… and responding to security incidents...

Open Console launches the admin interface… providing full administrative control...

This interface also has a dedicated session… so we'll continue to the final service card...

Login Info displays credentials… username admin at calfire dot gov… password admin...




The final card shows the Fire Risk Service… our machine learning prediction engine...

This service analyzes current conditions to calculate wildfire risk scores for geographic regions...





This landing page serves as the central hub for accessing all platform components.

It demonstrates a complete end-to-end solution… from data ingestion through storage tiers to user-facing analytics.

Challenge One deliverables include data ingestion from twelve sources… validation with Avro schemas… and latency monitoring dashboards.

Challenge Two deliverables feature hybrid storage across four tiers… cost optimization achieving ninety-seven point five percent savings… and comprehensive infrastructure monitoring.

Challenge Three deliverables encompass self-service data access… role-based dashboards for five user personas… and real-time analytics platform monitoring.

All components run in Docker containers… started with a single docker-compose up command… demonstrating operational simplicity.

The platform scales horizontally… adding container replicas to handle increased load… and vertically… upgrading individual service resources as needed.

It implements production-ready features… including authentication and authorization… audit logging… error handling… and health monitoring.

It achieves target performance metrics… with HOT tier queries under one hundred milliseconds… WARM tier queries under five hundred milliseconds… and API response times under two hundred milliseconds at the ninety-fifth percentile.

The live metrics displayed on this landing page… updating continuously… prove the platform is operational… not just slides or mockups… validating competition readiness for real-world deployment.


Thank you for exploring the Wildfire Intelligence Platform landing page… the gateway to a comprehensive wildfire data management and analytics solution.

