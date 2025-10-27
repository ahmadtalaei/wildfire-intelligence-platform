
Welcome to the Challenge Three Analytics Platform Monitoring Dashboard… a comprehensive real-time monitoring system tracking user activity… query performance… and data consumption across role-based interfaces.

Before we begin… ensure your Docker Compose environment is running… as this dashboard displays live streaming data from actual user sessions and query executions.


Open your web browser and navigate to localhost port three thousand ten.

You will see the Grafana login page.

Enter the username… admin… all lowercase.

Then the password… also admin… all lowercase.

Click Sign In to access the Grafana dashboard interface.


Once logged in… locate the Challenge Three Analytics Platform dashboard.

Click on Dashboards in the left sidebar.

Search for Challenge Three or Analytics Platform… or scroll through the list to find it.

Click on the dashboard name to open it.

If you need to import the dashboard from the JSON file… click the plus icon… select Import dashboard… then upload the file from monitoring slash grafana slash dashboards slash challenge3 analytics dashboard json file.


Please note that the metrics shown reflect demo user activity and query executions… Still, the dashboard refreshes every sixty seconds… to provide near real-time visibility into platform usage… performance… and user behavior.



Below the title… notice the User Role-Specific Metrics section.

At the top of this section… you'll see the current role displayed… such as Data Scientist.

All metrics on this dashboard are filtered by the selected user role… demonstrating our role-based access control implementation.

To switch roles… click the dropdown variable selector at the top of the dashboard… and choose from Data Scientist… Data Analyst… Fire Chief… Admin… or Field Responder.

Each role sees different activity levels and usage patterns… validating our Challenge Three requirement for role-specific interfaces.



The first row displays three critical performance indicators.

The Analytics Queries panel shows the total number of queries executed by the current role during the selected time period.

This metric tracks how actively users are querying the data clearing house… whether through SQL… REST APIs… or GraphQL endpoints.

The Average Query Response panel displays query performance in milliseconds.

Fast response times ensure data scientists and analysts can work efficiently… meeting our sub-two hundred millisecond performance target for the ninety-fifth percentile.

The Active User Sessions panel shows how many users with the current role are actively working in the platform.

Active sessions indicate real-time engagement with the analytics platform… validating user adoption and platform value.



The second row tracks user outputs and platform engagement.

The Reports Generated panel counts reports created by users during the time period.

This validates our Challenge Three deliverable for report generation capabilities… allowing analysts to produce formatted outputs for stakeholders.

The Data Exports panel tracks successful data exports… showing how many times users downloaded datasets in CSV… JSON… GeoJSON… Parquet… or Excel formats.

High export volumes demonstrate self-service data access… a core Challenge Three requirement.

The Platform Usage percentage shows the ratio of active sessions to total sessions… indicating platform adoption and user engagement.

High usage percentages confirm users find value in the analytics platform… validating our user-centric dashboard design.



Below the stat panels… a time-series chart displays Role-Based Analytics Activity.

This chart shows query volume over time… color-coded by query type.

You'll see three distinct lines representing REST API calls… GraphQL queries… and direct SQL queries.

The chart reveals usage patterns throughout the day… showing peak activity periods when analysts run complex queries… and quieter periods overnight.

This time-series visualization helps capacity planners understand when users need the most resources… and when maintenance windows can be scheduled.

The chart demonstrates that our platform supports multiple query methods… giving users flexibility to choose the best approach for their analysis.



Next to the time-series chart… the Analytics Platform Distribution pie chart shows the proportional breakdown of query types.

Three slices represent REST API… GraphQL… and SQL queries.

This distribution validates our Challenge Three requirement for multiple access patterns… ensuring users can query data through their preferred interface.

Data scientists often prefer SQL for complex joins and aggregations… while analysts favor REST APIs for simpler filtered queries… and GraphQL for navigating related data.

A balanced distribution across all three types confirms our platform serves diverse user needs… a key Challenge Three deliverable for self-service analytics.



Below the charts… the Real-Time Query Activity Log section provides a detailed view of individual query executions.

This section header introduces the live query monitoring table… which updates every minute with the latest activity.



The table displays the twenty most recent queries… showing comprehensive details for each execution.

Six columns provide complete visibility into user activity.

The User Activity column shows the query type… whether REST API… GraphQL… or SQL.

The Dataset Accessed column identifies which data source was queried… such as fire detection data… weather station records… or satellite imagery metadata.

The Records Processed column shows how many rows were returned… indicating query result size.

Large result sets may indicate users exporting bulk data… while small result sets suggest targeted queries for specific incidents.

The Query Time column displays execution duration in milliseconds… tracking performance at the individual query level.

Fast queries validate our database indexing and caching strategies… while slow queries may require optimization.

The Status column shows success or failure… helping identify issues with query syntax… permissions… or data availability.

High success rates confirm our platform is stable and user-friendly.

The Session Time column timestamps each query… allowing correlation with user sessions and activity patterns.



This dashboard demonstrates our Challenge Three data clearing house implementation.

Users from different roles access a shared data repository through standardized APIs and query interfaces.

The dashboard tracks who accesses what data… when… and how… providing comprehensive audit trails for security and compliance.

Data scientists query raw datasets for machine learning model training.

Analysts generate reports and visualizations for executive briefings.

Fire chiefs access real-time fire detection data for operational decision-making.

All activity flows through the data clearing house… with this dashboard providing complete visibility.

Operations teams monitor query performance to ensure service level agreements are met… guaranteeing fast response times for time-sensitive fire intelligence queries.
Security teams track user activity to detect anomalous behavior… ensuring data access policies are enforced.

Product managers analyze usage patterns to understand which features users value most… guiding platform enhancements and feature prioritization.

Executive sponsors see adoption metrics demonstrating return on investment from the analytics platform implementation.

Data governance teams validate that all data access is logged and auditable… meeting FISMA compliance requirements for government systems.

Security and Governance deliverables are validated through comprehensive query tracking… session monitoring… and access logging.

Backend and Processing deliverables are demonstrated through query performance metrics… multi-format export support… and real-time data pipeline monitoring.





This dashboard transforms analytics platform metrics into actionable intelligence for platform administrators and business stakeholders.



Security teams track user activity to detect anomalous behavior… ensuring data access policies are enforced.

Product managers analyze usage patterns to understand which features users value most… guiding platform enhancements and feature prioritization.

Executive sponsors see adoption metrics demonstrating return on investment from the analytics platform implementation.

Data governance teams validate that all data access is logged and auditable… meeting FISMA compliance requirements for government systems.



The live metrics demonstrate platform scalability under real-world workloads.

Multiple concurrent users from different roles query the platform simultaneously… with the system maintaining fast response times.



