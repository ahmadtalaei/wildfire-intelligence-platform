## Slide 13: Self-Service Portal Introduction

### Visual Content

```
SELF-SERVICE DATA ACCESS PORTAL
═══════════════════════════════════════════════════════════════

PORTAL ARCHITECTURE:
┌─────────────────────────────────────────────────────────────┐
│  USER INTERFACE LAYER                                        │
├─────────────────────────────────────────────────────────────┤
│  • Visual Query Builder (No SQL Required)                   │
│  • SQL Editor (Advanced Users)                              │
│  • Saved Query Library                                       │
│  • Data Export Manager                                       │
│  • Usage Dashboard                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  QUERY ENGINE                                                │
├─────────────────────────────────────────────────────────────┤
│  • Query Validation & Optimization                           │
│  • Permission Enforcement                                    │
│  • Result Caching (70% hit rate)                            │
│  • Rate Limiting (1,000 req/hour/user)                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  DATA ACCESS LAYER                                           │
├─────────────────────────────────────────────────────────────┤
│  HOT (0-7 days)    PostgreSQL    <100ms response            │
│  WARM (7-90 days)  Parquet/MinIO <500ms response            │
│  COLD (90+ days)   S3 Standard-IA <5s response              │
└─────────────────────────────────────────────────────────────┘

SUPPORTED QUERY TYPES:
═══════════════════════════════════════════════════════════════

┌──────────────────┬────────────────────────────────────────┐
│ FIRE DATA        │ • Historical fire incidents            │
│                  │ • Real-time fire detections            │
│                  │ • Fire perimeter evolution             │
│                  │ • Risk assessment scores               │
├──────────────────┼────────────────────────────────────────┤
│ WEATHER DATA     │ • Current weather conditions           │
│                  │ • Historical weather patterns          │
│                  │ • Fire weather indices                 │
│                  │ • Forecast data                        │
├──────────────────┼────────────────────────────────────────┤
│ SATELLITE DATA   │ • Satellite imagery metadata           │
│                  │ • Multi-spectral analysis results      │
│                  │ • Thermal anomaly detection            │
│                  │ • Change detection                     │
├──────────────────┼────────────────────────────────────────┤
│ SENSOR DATA      │ • IoT sensor readings                  │
│                  │ • Air quality measurements             │
│                  │ • Smoke detection alerts               │
│                  │ • Network health status                │
├──────────────────┼────────────────────────────────────────┤
│ COMBINED QUERIES │ • Multi-source correlation             │
│                  │ • Spatial-temporal joins               │
│                  │ • Aggregated analytics                 │
│                  │ • Custom reports                       │
└──────────────────┴────────────────────────────────────────┘

KEY FEATURES:
═══════════════════════════════════════════════════════════════

✓ No SQL knowledge required for basic queries
✓ Advanced SQL editor for power users
✓ Geographic filter tools (bounding box, radius, polygon)
✓ Temporal filters (date range, time of day, relative windows)
✓ Data source selection and filtering
✓ Quality threshold controls
✓ Export to multiple formats (CSV, JSON, Parquet, Excel)
✓ Save and share query templates
✓ Usage tracking and quota management
✓ Query history and favorites
```

### 🎤 **Speaker Script**

The Self Service Data Access Portal empowers users to access wildfire data without technical barriers.

Our portal architecture consists of three distinct layers.

The user interface layer provides both a visual query builder for users without S Q L knowledge… and an advanced S Q L editor for power users.

It includes a saved query library for reusing common queries… a data export manager for downloading results… and a usage dashboard for monitoring activity.


The query engine handles validation and optimization automatically.

Permission enforcement ensures users only access authorized data.

Result caching achieves a seventy percent hit rate… dramatically reducing query execution time.

Rate limiting maintains system performance at one thousand requests per hour per user.


The data access layer routes queries to appropriate storage tiers based on data age.

HOT tier data from the last zero to seven days… stored in PostgreSQL… delivers results in under one hundred milliseconds.

WARM tier data from seven to ninety days… stored as Parquet on MinIO… responds in under five hundred milliseconds.

COLD tier data beyond ninety days… archived in S three Standard I A… responds in under five seconds.


We support five major query types.

Fire data queries access historical fire incidents… real time fire detections… fire perimeter evolution… and risk assessment scores.

Weather data queries retrieve current weather conditions… historical weather patterns… fire weather indices… and forecast data.

Satellite data queries provide satellite imagery metadata… multi spectral analysis results… thermal anomaly detection… and change detection analytics.

Sensor data queries deliver I o T sensor readings… air quality measurements… smoke detection alerts… and network health status.

Combined queries enable multi source correlation… spatial temporal joins… aggregated analytics… and custom report generation.


Key features ensure accessibility and usability.

No S Q L knowledge is required for basic queries thanks to the visual query builder.

Advanced users can use the S Q L editor for complex analytical work.

Geographic filter tools support bounding box selection… radius from point… and custom polygon drawing.

Temporal filters include date range pickers… time of day restrictions… and relative time windows.

Data source selection enables filtering by specific satellites… weather stations… or sensor networks.

Quality threshold controls ensure users receive only high quality validated data.

Export functionality supports C S V… JSON… Parquet… and Excel formats.

Query templates can be saved and shared across teams.

Usage tracking and quota management prevent resource exhaustion.

And query history with favorites enables quick access to frequently used queries.

This comprehensive portal democratizes access to wildfire intelligence data… enabling CAL FIRE and partner organizations to derive insights without technical dependencies.

---

## Slide 14: Query Builder Interface

### Visual Content

```
VISUAL QUERY BUILDER INTERFACE
═══════════════════════════════════════════════════════════════

STEP 1: SELECT DATA SOURCE
┌─────────────────────────────────────────────────────────────┐
│  ○ Fire Detection Data                                       │
│     └─ NASA FIRMS (Real-time satellite detections)          │
│  ○ Weather Observations                                      │
│     └─ NOAA Stations + IoT Sensors                          │
│  ○ Satellite Imagery Metadata                                │
│     └─ Landsat, Sentinel, MODIS                             │
│  ○ CAL FIRE Incident Reports                                 │
│     └─ Official incident records                             │
│  ⦿ Combined Data Sources                                     │
│     └─ Multi-source correlation queries                      │
└─────────────────────────────────────────────────────────────┘

STEP 2: ADD FILTERS (Visual Builder)
┌─────────────────────────────────────────────────────────────┐
│  FILTER 1:                                                   │
│  Field: [Acres Burned ▾]                                     │
│  Operator: [Greater Than ▾]                                  │
│  Value: [5000] acres                                         │
│  [Remove Filter] [Add Another Filter]                        │
│                                                              │
│  FILTER 2:                                                   │
│  Field: [Containment Percent ▾]                              │
│  Operator: [Less Than ▾]                                     │
│  Value: [50] %                                               │
│  [Remove Filter] [Add Another Filter]                        │
│                                                              │
│  FILTER 3:                                                   │
│  Field: [Confidence Level ▾]                                 │
│  Operator: [Greater Than or Equal ▾]                         │
│  Value: [80] %                                               │
│  [Remove Filter] [+ Add Another Filter]                      │
└─────────────────────────────────────────────────────────────┘

STEP 3: GEOGRAPHIC BOUNDS (Map-Based Selection)
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                   CALIFORNIA                        │    │
│  │         ╔═══════════════════════╗                  │    │
│  │         ║  NORTHERN CALIFORNIA  ║                  │    │
│  │         ║                       ║                  │    │
│  │         ║   Selected Region     ║                  │    │
│  │         ║                       ║                  │    │
│  │         ╚═══════════════════════╝                  │    │
│  │                                                     │    │
│  │                                                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Selection Type: [Bounding Box ▾]                           │
│  Latitude: 37.0° to 42.0° N                                 │
│  Longitude: -125.0° to -119.0° W                            │
│                                                              │
│  Alternative Methods:                                        │
│  • Radius from Point (1-500 km)                             │
│  • County/Region Selection                                  │
│  • Custom Polygon Drawing                                   │
└─────────────────────────────────────────────────────────────┘

STEP 4: TIME RANGE SELECTION
┌─────────────────────────────────────────────────────────────┐
│  Time Range Type: [Absolute Date Range ▾]                   │
│                                                              │
│  Start Date: [2024-10-01] [Calendar Icon]                   │
│  End Date:   [2024-10-20] [Calendar Icon]                   │
│                                                              │
│  Quick Presets:                                              │
│  [Last 24 Hours] [Last 7 Days] [Last 30 Days]               │
│  [Last 90 Days] [This Year] [Custom]                        │
│                                                              │
│  Time of Day Filter (Optional):                              │
│  From: [06:00] To: [18:00] (Daylight hours only)            │
│                                                              │
│  Day of Week Filter (Optional):                              │
│  ☑ Monday  ☑ Tuesday  ☑ Wednesday  ☑ Thursday  ☑ Friday     │
│  ☑ Saturday  ☑ Sunday                                        │
└─────────────────────────────────────────────────────────────┘

STEP 5: SELECT OUTPUT FIELDS
┌─────────────────────────────────────────────────────────────┐
│  Available Fields (20 total)        Selected Fields (6)     │
│  ┌───────────────────────┐          ┌──────────────────┐   │
│  │ ☐ Fire ID             │          │ ☑ Incident Name  │   │
│  │ ☑ Incident Name       │     >>   │ ☑ Latitude       │   │
│  │ ☑ Latitude            │          │ ☑ Longitude      │   │
│  │ ☑ Longitude           │     <<   │ ☑ Acres Burned   │   │
│  │ ☑ Acres Burned        │          │ ☑ Containment %  │   │
│  │ ☐ Brightness Temp     │          │ ☑ Detection Time │   │
│  │ ☑ Containment %       │          └──────────────────┘   │
│  │ ☑ Detection Time      │                                  │
│  │ ☐ Confidence Level    │          [↑ Move Up]             │
│  │ ☐ Fire Radiative Power│          [↓ Move Down]           │
│  │ ☐ Satellite Source    │          [Remove Selected]       │
│  └───────────────────────┘                                  │
│                                                              │
│  [Select All] [Clear All] [Common Presets ▾]                │
└─────────────────────────────────────────────────────────────┘

STEP 6: PREVIEW & EXECUTE
┌─────────────────────────────────────────────────────────────┐
│  QUERY SUMMARY                                               │
│  ──────────────────────────────────────────────────────────  │
│  Data Source: Fire Detection Data                           │
│  Filters: 3 active filters                                   │
│    • Acres Burned > 5000                                     │
│    • Containment % < 50                                      │
│    • Confidence >= 80%                                       │
│  Geographic: Northern California (Bounding Box)              │
│  Time Range: Oct 1-20, 2024 (20 days)                       │
│  Fields: 6 selected                                          │
│  Estimated Results: ~150 records                             │
│  Estimated Query Time: <500ms                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Sample Preview (First 3 rows):                       │   │
│  ├────────┬──────────┬───────────┬──────────┬────────── │   │
│  │ Name   │ Lat      │ Lon       │ Acres    │ Contain  │   │
│  ├────────┼──────────┼───────────┼──────────┼──────────┤   │
│  │ Fire A │ 39.7596  │ -121.6219 │ 12,500   │ 25%      │   │
│  │ Fire B │ 40.1234  │ -122.4567 │ 8,750    │ 40%      │   │
│  │ Fire C │ 38.9876  │ -120.1234 │ 6,200    │ 15%      │   │
│  └────────┴──────────┴───────────┴──────────┴──────────┘   │
│                                                              │
│  Actions:                                                    │
│  [Execute Query] [Save as Template] [Export Settings]       │
│  [Schedule Recurring] [Share with Team]                     │
└─────────────────────────────────────────────────────────────┘

SAVED QUERY TEMPLATES (Quick Access):
═══════════════════════════════════════════════════════════════

★ Active Large Fires (Last 30 Days)
  • Acres > 1000, Containment < 50%, California-wide
  • Used 247 times this month

★ High Confidence Fire Detections (Last 24 Hours)
  • Confidence >= 85%, All sources, Real-time
  • Used 189 times this month

★ Northern California Weather Risk
  • Humidity < 25%, Wind > 25 mph, Last 7 days
  • Used 156 times this month

★ Historical Pattern Analysis (2020-2024)
  • All counties, Quality score >= 90, With weather data
  • Used 89 times this month
```

### 🎤 **Speaker Script**

Our visual query builder guides users through six simple steps to construct powerful data queries.

Step One is selecting the data source.

Users choose from fire detection data sourced from NASA FIRMS real time satellite detections.

Weather observations combine NOAA stations with I o T sensors.

Satellite imagery metadata covers Landsat… Sentinel… and MODIS platforms.

CAL FIRE incident reports provide official incident records.

And combined data sources enable multi source correlation queries.


Step Two involves adding filters using the visual builder.

Each filter consists of three components… a field… an operator… and a value.

For example… Filter One selects the acres burned field… applies a greater than operator… and sets the value to five thousand acres.

Filter Two selects containment percent… uses less than… and sets fifty percent.

Filter Three chooses confidence level… applies greater than or equal… and sets eighty percent.

Users can add unlimited filters and remove any filter with one click.


Step Three provides geographic bounds selection using an interactive map.

Users can select a bounding box by drawing directly on the California map.

Our example shows Northern California selected… with latitude from thirty seven point zero to forty two point zero degrees north… and longitude from negative one hundred twenty five to negative one hundred nineteen degrees west.

Alternative methods include radius from point supporting one to five hundred kilometers… county or region selection using administrative boundaries… and custom polygon drawing for precise geographic definitions.


Step Four handles time range selection with multiple options.

Users select absolute date ranges using calendar pickers.

Our example shows October first through October twentieth… twenty twenty four… spanning twenty days.

Quick presets provide one click access to common ranges… last twenty four hours… last seven days… last thirty days… last ninety days… this year… or custom.

Optional time of day filters restrict results to specific hours… like zero six hundred to eighteen hundred for daylight hours only.

Day of week filters enable analysis of weekday versus weekend patterns.


Step Five lets users select output fields.

The left panel shows all available fields… twenty total in this example.

The right panel displays selected fields… six in our example.

Users drag fields between panels or use arrow buttons.

Selected fields can be reordered using move up and move down buttons.

Common presets provide one click field selection for typical use cases.


Step Six presents a query summary with preview and execution options.

The summary displays all query parameters for final review.

Data source shows fire detection data.

Three active filters are listed.

Geographic bounds show Northern California bounding box.

Time range confirms October first through twentieth… twenty twenty four.

Six fields are selected for output.

Estimated results predict approximately one hundred fifty records.

Estimated query time is under five hundred milliseconds.


A sample preview shows the first three rows of expected results.

Fire A at thirty nine point seven five nine six latitude… negative one hundred twenty one point six two one nine longitude… twelve thousand five hundred acres… twenty five percent contained.

Fire B and Fire C follow similar patterns.


Action buttons provide multiple options.

Execute query runs the query immediately.

Save as template stores the configuration for reuse.

Export settings generates a shareable query definition.

Schedule recurring enables automated execution.

And share with team distributes the query to colleagues.


Below the builder… saved query templates provide quick access to common queries.

Active Large Fires from the last thirty days… filtering for acres greater than one thousand and containment less than fifty percent… has been used two hundred forty seven times this month.

High Confidence Fire Detections from the last twenty four hours… requiring confidence greater than or equal to eighty five percent… has been used one hundred eighty nine times.

Northern California Weather Risk… filtering for humidity below twenty five percent and wind above twenty five miles per hour… has been used one hundred fifty six times.

Historical Pattern Analysis spanning twenty twenty through twenty twenty four… requiring quality score above ninety and including weather data… has been used eighty nine times.


This intuitive interface democratizes data access… enabling users at all skill levels to extract actionable wildfire intelligence.

---

## Slide 15: Data Export Capabilities

### Visual Content

```
DATA EXPORT CAPABILITIES
═══════════════════════════════════════════════════════════════

EXPORT FORMATS SUPPORTED:
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  TABULAR FORMATS                                             │
│  ────────────────────────────────────────────                │
│  ✓ CSV (Comma-Separated Values)                             │
│     • Universal compatibility                                │
│     • UTF-8 encoding with BOM                                │
│     • Configurable delimiter (comma, tab, pipe)             │
│     • Header row included                                    │
│     • Max size: Unlimited (streaming export)                │
│                                                              │
│  ✓ Excel (XLSX)                                              │
│     • Multiple worksheets support                            │
│     • Formatted headers and auto-width columns              │
│     • Data type preservation (dates, numbers, text)         │
│     • Max size: 1 million rows per sheet                    │
│     • Includes metadata sheet with query details            │
│                                                              │
│  ✓ JSON (JavaScript Object Notation)                        │
│     • Hierarchical data structure                            │
│     • Array of objects or nested format                     │
│     • Pretty-print or compact modes                          │
│     • Schema validation included                             │
│     • Max size: Unlimited (streaming)                        │
│                                                              │
│  ✓ Parquet (Apache Parquet)                                  │
│     • Columnar storage format                                │
│     • Highly compressed (70-85% size reduction)             │
│     • Optimized for analytics                                │
│     • Schema embedded in file                                │
│     • Compatible with Spark, Pandas, Arrow                  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  GEOSPATIAL FORMATS                                          │
│  ──────────────────                                          │
│  ✓ GeoJSON                                                   │
│     • Geographic features as JSON                            │
│     • Point, LineString, Polygon support                    │
│     • CRS (Coordinate Reference System) included            │
│     • Compatible with web mapping libraries                 │
│                                                              │
│  ✓ Shapefile (ESRI SHP)                                      │
│     • Industry standard GIS format                           │
│     • Includes .shp, .shx, .dbf, .prj files                 │
│     • Compatible with ArcGIS, QGIS                          │
│     • Attribute table included                               │
│                                                              │
│  ✓ KML/KMZ (Keyhole Markup Language)                        │
│     • Google Earth compatible                                │
│     • Styled markers and polygons                            │
│     • Embedded descriptions and metadata                     │
│     • KMZ includes compression                               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  REPORT FORMATS                                              │
│  ──────────────                                              │
│  ✓ PDF (Portable Document Format)                           │
│     • Publication-ready reports                              │
│     • Embedded charts and maps                               │
│     • Multi-page support                                     │
│     • Searchable text                                        │
│     • Custom headers/footers with CAL FIRE branding         │
│                                                              │
│  ✓ HTML (HyperText Markup Language)                         │
│     • Interactive web reports                                │
│     • Sortable tables                                        │
│     • Embedded visualizations                                │
│     • Responsive design for mobile                           │
│     • Share via URL or email                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘

EXPORT WORKFLOW:
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  STEP 1: SELECT EXPORT FORMAT                                │
│                                                              │
│  Format: [CSV ▾]                                             │
│                                                              │
│  CSV Options:                                                │
│  • Delimiter: [Comma ▾] (Comma, Tab, Pipe, Semicolon)       │
│  • Include Header: [Yes ▾]                                   │
│  • Quote All Fields: [No ▾]                                  │
│  • Encoding: [UTF-8 ▾]                                       │
│  • Compression: [None ▾] (None, ZIP, GZIP)                   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  STEP 2: CONFIGURE OPTIONS                                   │
│                                                              │
│  ☑ Include Metadata Header                                   │
│     (Query details, execution time, record count)            │
│                                                              │
│  ☑ Apply Data Quality Filters                                │
│     Only export records with quality score >= [90]           │
│                                                              │
│  ☐ Anonymize Sensitive Fields                                │
│     (Remove PII or sensitive location data)                  │
│                                                              │
│  ☑ Generate Checksum File                                    │
│     (SHA-256 hash for data integrity verification)          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  STEP 3: DELIVERY METHOD                                     │
│                                                              │
│  ○ Direct Download (Files < 100 MB)                          │
│     Download begins immediately after export completes       │
│                                                              │
│  ⦿ Email Notification with Download Link                     │
│     Email: [user@calfire.ca.gov]                            │
│     Link expires in: [7 days ▾]                              │
│                                                              │
│  ○ Upload to Cloud Storage                                   │
│     S3 Bucket: [s3://calfire-data-exports/]                 │
│     Path: [/user_exports/2024/10/]                           │
│                                                              │
│  ○ Transfer to SFTP Server                                   │
│     Server: [sftp.partner.org]                              │
│     Username: [partner_user]                                 │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  STEP 4: SCHEDULE (OPTIONAL)                                 │
│                                                              │
│  ○ One-Time Export (Execute Now)                             │
│  ⦿ Recurring Export Schedule                                 │
│                                                              │
│  Frequency: [Daily ▾] (Hourly, Daily, Weekly, Monthly)      │
│  Time: [02:00] PST                                           │
│  Start Date: [2024-10-21]                                    │
│  End Date: [2024-12-31] (Optional)                           │
│                                                              │
│  Notification Email: [user@calfire.ca.gov]                  │
│  ☑ Only send email if data changes                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘

EXPORT TRACKING DASHBOARD:
═══════════════════════════════════════════════════════════════

Recent Exports (Last 30 Days):
┌──────────────┬────────────┬────────┬──────────┬──────────────┐
│ Export ID    │ Format     │ Size   │ Status   │ Download     │
├──────────────┼────────────┼────────┼──────────┼──────────────┤
│ EXP-2847     │ CSV        │ 23 MB  │ Complete │ [Download]   │
│ Created: Oct 20, 2024 14:30 | Records: 125,000               │
│ Query: Active Large Fires (Last 30 Days)                     │
├──────────────┼────────────┼────────┼──────────┼──────────────┤
│ EXP-2846     │ GeoJSON    │ 8 MB   │ Complete │ [Download]   │
│ Created: Oct 20, 2024 10:15 | Records: 45,000                │
│ Query: Northern CA Fire Perimeters                           │
├──────────────┼────────────┼────────┼──────────┼──────────────┤
│ EXP-2845     │ Excel      │ 156 MB │ Complete │ [Download]   │
│ Created: Oct 19, 2024 22:45 | Records: 850,000               │
│ Query: Historical Weather-Fire Correlation (2020-2024)       │
├──────────────┼────────────┼────────┼──────────┼──────────────┤
│ EXP-2844     │ Parquet    │ 42 MB  │ Complete │ [Download]   │
│ Created: Oct 19, 2024 15:20 | Records: 500,000               │
│ Query: NASA FIRMS Data (Q3 2024)                             │
├──────────────┼────────────┼────────┼──────────┼──────────────┤
│ EXP-2843     │ PDF Report │ 12 MB  │ Complete │ [Download]   │
│ Created: Oct 18, 2024 09:00 | Pages: 47                      │
│ Query: Monthly Fire Statistics Report (September 2024)       │
└──────────────┴────────────┴────────┴──────────┴──────────────┘

Usage Statistics:
• Total Exports This Month: 89
• Total Data Exported: 2.4 TB
• Most Popular Format: CSV (45%), Parquet (28%), Excel (18%)
• Average Export Size: 27 MB
• Quota Remaining: 8.2 TB of 10 TB monthly limit
```

### 🎤 **Speaker Script**

Our data export capabilities provide comprehensive format support and flexible delivery options.

We support three categories of export formats.


Tabular formats handle structured data efficiently.

C S V or comma separated values… offers universal compatibility.

We use U T F eight encoding with B O M.

Delimiters are configurable… comma… tab… pipe… or semicolon.

Header rows are included by default.

Maximum size is unlimited thanks to streaming export technology.


Excel X L S X format supports multiple worksheets.

Headers are formatted and columns auto sized.

Data types are preserved… dates… numbers… and text maintain their formats.

Maximum size is one million rows per sheet.

Each export includes a metadata sheet with query details.


JSON or JavaScript Object Notation… handles hierarchical data structures.

We support array of objects or nested format styles.

Pretty print or compact modes optimize for readability or size.

Schema validation ensures data integrity.

Maximum size is unlimited using streaming export.


Parquet or Apache Parquet… uses columnar storage format.

Highly compressed… achieving seventy to eighty five percent size reduction.

Optimized for analytical workloads.

Schema is embedded in the file.

Compatible with Spark… Pandas… and Arrow frameworks.


Geospatial formats enable G I S integration.

GeoJSON represents geographic features as JSON.

Point… LineString… and Polygon geometries are supported.

Coordinate reference systems are included.

Compatible with all major web mapping libraries.


Shapefile follows the ESRI S H P industry standard.

Exports include dot S H P… dot S H X… dot D B F… and dot P R J files.

Compatible with ArcGIS and Q G I S.

Attribute tables are included with full metadata.


K M L and K M Z use Keyhole Markup Language.

Google Earth compatible for instant visualization.

Styled markers and polygons enhance presentation.

Embedded descriptions provide context.

K M Z includes compression for smaller file sizes.


Report formats deliver publication ready outputs.

P D F or Portable Document Format… produces publication ready reports.

Charts and maps are embedded directly.

Multi page support handles large datasets.

Text is searchable for easy navigation.

Custom headers and footers include CAL FIRE branding.


H T M L or HyperText Markup Language… creates interactive web reports.

Tables are sortable for dynamic exploration.

Visualizations are embedded and interactive.

Responsive design ensures mobile compatibility.

Reports can be shared via U R L or email.


The export workflow consists of four simple steps.

Step One selects the export format and options.

Users choose from the dropdown… C S V in this example.

C S V specific options include delimiter selection… header inclusion… quote all fields toggle… encoding choice… and compression method.


Step Two configures additional options.

Include metadata header adds query details… execution time… and record count.

Apply data quality filters exports only records with quality score above ninety.

Anonymize sensitive fields removes P I I or sensitive location data when needed.

Generate checksum file creates S H A two fifty six hash for data integrity verification.


Step Three determines delivery method.

Direct download works for files under one hundred megabytes… beginning immediately after export completes.

Email notification with download link sends a secure link that expires after seven days.

Upload to cloud storage places files directly in S three buckets at specified paths.

Transfer to S F T P server enables integration with partner systems.


Step Four handles optional scheduling.

One time export executes immediately.

Recurring export schedule supports hourly… daily… weekly… or monthly frequency.

Time is configurable with timezone support.

Start and end dates define the active period.

Notification email alerts users to completion.

An option to only send email if data changes reduces notification noise.


The export tracking dashboard displays recent activity.

Export I D two thousand eight hundred forty seven… C S V format… twenty three megabytes… completed successfully… ready for download.

Created October twentieth twenty twenty four at fourteen thirty.

One hundred twenty five thousand records exported.

Query was Active Large Fires from the last thirty days.


Export I D two thousand eight hundred forty six… GeoJSON format… eight megabytes… completed.

Forty five thousand records.

Query was Northern California fire perimeters.


Export I D two thousand eight hundred forty five… Excel format… one hundred fifty six megabytes.

Eight hundred fifty thousand records.

Historical weather fire correlation from twenty twenty through twenty twenty four.


Export I D two thousand eight hundred forty four… Parquet format… forty two megabytes compressed.

Five hundred thousand records.

NASA FIRMS data from Q three twenty twenty four.


Export I D two thousand eight hundred forty three… P D F report… twelve megabytes.

Forty seven pages.

Monthly fire statistics report for September twenty twenty four.


Usage statistics track consumption patterns.

Total exports this month… eighty nine.

Total data exported… two point four terabytes.

Most popular format… C S V at forty five percent… followed by Parquet at twenty eight percent… and Excel at eighteen percent.

Average export size is twenty seven megabytes.

Quota remaining shows eight point two terabytes of ten terabyte monthly limit.


This comprehensive export system ensures users can access wildfire data in their preferred format… delivered through their preferred method… on their preferred schedule.

---

## Slide 16: Security Framework Overview

### Visual Content

```
SECURITY FRAMEWORK OVERVIEW
═══════════════════════════════════════════════════════════════

MULTI-LAYERED SECURITY ARCHITECTURE:

┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: AUTHENTICATION                                     │
├─────────────────────────────────────────────────────────────┤
│  • OAuth 2.0 / OIDC Integration                              │
│  • SAML 2.0 SSO (Single Sign-On)                            │
│  • Multi-Factor Authentication (TOTP-based)                  │
│  • JWT Token-Based Sessions                                  │
│  • Session Timeout: 24 hours with auto-refresh              │
│  • Password Policy: 12+ chars, complexity required          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: AUTHORIZATION                                      │
├─────────────────────────────────────────────────────────────┤
│  • Role-Based Access Control (RBAC)                          │
│  • Attribute-Based Access Control (ABAC)                     │
│  • Least Privilege Principle                                 │
│  • Permission Inheritance & Delegation                       │
│  • Temporary Access Grants with Expiration                   │
│  • Emergency Override Procedures (Logged)                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: DATA PROTECTION                                    │
├─────────────────────────────────────────────────────────────┤
│  • Encryption at Rest: AES-256                               │
│  • Encryption in Transit: TLS 1.3                            │
│  • Key Management: AWS KMS / HashiCorp Vault                 │
│  • Data Masking for Sensitive Fields                         │
│  • Row-Level Security Policies                               │
│  • Column-Level Encryption for PII                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: AUDIT & MONITORING                                 │
├─────────────────────────────────────────────────────────────┤
│  • Comprehensive Audit Logging                               │
│  • Real-Time Anomaly Detection                               │
│  • Security Event Correlation                                │
│  • Automated Alert Generation                                │
│  • Forensic Investigation Tools                              │
│  • Compliance Reporting                                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: NETWORK SECURITY                                   │
├─────────────────────────────────────────────────────────────┤
│  • API Gateway Rate Limiting                                 │
│  • DDoS Protection                                           │
│  • Web Application Firewall (WAF)                            │
│  • IP Whitelisting / Blacklisting                            │
│  • VPN Required for External Access                          │
│  • Network Segmentation (DMZ, Internal, Data Zones)         │
└─────────────────────────────────────────────────────────────┘

SECURITY POLICIES IMPLEMENTED:
═══════════════════════════════════════════════════════════════

┌──────────────────────┬──────────────────────────────────────┐
│ POLICY NAME          │ DETAILS                              │
├──────────────────────┼──────────────────────────────────────┤
│ Data Classification  │ • PUBLIC: Weather data, historical   │
│                      │ • INTERNAL: Fire incidents, reports  │
│                      │ • RESTRICTED: Predictive models, AI  │
│                      │ • CONFIDENTIAL: Emergency response   │
│                      │ • SECRET: Critical infrastructure    │
├──────────────────────┼──────────────────────────────────────┤
│ Access Level Mapping │ Classification → Minimum Role        │
│                      │ • PUBLIC → Viewer                    │
│                      │ • INTERNAL → Analyst                 │
│                      │ • RESTRICTED → Data Scientist        │
│                      │ • CONFIDENTIAL → Fire Chief          │
│                      │ • SECRET → System Admin              │
├──────────────────────┼──────────────────────────────────────┤
│ Data Retention       │ • Fire Data: 7 years (FISMA req)     │
│                      │ • Weather Data: 3 years              │
│                      │ • Audit Logs: 7 years (compliance)   │
│                      │ • Temp/Cache: 24 hours               │
│                      │ • Legal Hold: Indefinite freeze      │
├──────────────────────┼──────────────────────────────────────┤
│ Encryption Standards │ • Data at Rest: AES-256-GCM          │
│                      │ • Data in Transit: TLS 1.3           │
│                      │ • Key Rotation: Every 90 days        │
│                      │ • Key Storage: Hardware Security     │
│                      │   Module (HSM) or AWS KMS            │
├──────────────────────┼──────────────────────────────────────┤
│ Audit Requirements   │ • All data access logged             │
│                      │ • Failed login attempts tracked      │
│                      │ • Config changes require approval    │
│                      │ • Export activities monitored        │
│                      │ • Anomalies trigger alerts           │
└──────────────────────┴──────────────────────────────────────┘

SECURITY METRICS & MONITORING:
═══════════════════════════════════════════════════════════════

Real-Time Security Dashboard:
┌─────────────────────────────────────────────────────────────┐
│  SECURITY HEALTH SCORE: 94/100 (Excellent)                   │
│                                                              │
│  Active Sessions:          247                               │
│  Failed Login Attempts:    3 (last 24h)                     │
│  Anomaly Alerts:           0 (last 24h)                     │
│  Audit Log Entries:        12,847 (last 24h)                │
│  Encryption Coverage:      100%                              │
│  Access Policy Violations: 1 (investigated)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SECURITY EVENTS (Last 7 Days)                        │   │
│  ├──────────────┬──────────┬─────────────────────────── │   │
│  │ Event Type   │ Count    │ Risk Level                │   │
│  ├──────────────┼──────────┼───────────────────────────┤   │
│  │ Login        │ 2,847    │ ▓░░░░ Low                 │   │
│  │ Data Access  │ 8,934    │ ▓░░░░ Low                 │   │
│  │ Export       │ 156      │ ▓▓░░░ Medium              │   │
│  │ Config Change│ 12       │ ▓▓▓░░ High                │   │
│  │ Failed Auth  │ 47       │ ▓▓░░░ Medium              │   │
│  │ Anomaly      │ 2        │ ▓▓▓▓░ High (Investigated) │   │
│  └──────────────┴──────────┴───────────────────────────┘   │
│                                                              │
│  Recent High-Risk Events:                                    │
│  🚨 Oct 19 15:47 - Multiple failed login attempts           │
│     User: unknown_user | IP: 192.168.5.234                  │
│     Action: IP blacklisted, Security team notified          │
│                                                              │
│  ⚠️ Oct 18 22:15 - After-hours data export                  │
│     User: analyst_005 | Dataset: Confidential Reports       │
│     Action: Reviewed, Authorized by supervisor              │
└─────────────────────────────────────────────────────────────┘

COMPLIANCE FRAMEWORK ALIGNMENT:
═══════════════════════════════════════════════════════════════

✓ FISMA (Federal Information Security Management Act)
  • Risk assessment completed
  • Security controls documented
  • Continuous monitoring enabled
  • Incident response plan active

✓ NIST 800-53 (Security and Privacy Controls)
  • Access Control (AC) family: 18 controls implemented
  • Audit & Accountability (AU) family: 12 controls implemented
  • Identification & Authentication (IA) family: 11 controls
  • System & Communications Protection (SC) family: 15 controls

✓ HIPAA (if health data processed)
  • Privacy Rule compliance
  • Security Rule compliance
  • Breach notification procedures

✓ California Consumer Privacy Act (CCPA)
  • Data inventory maintained
  • Consent management implemented
  • Right to deletion procedures
  • Privacy notices provided

✓ SOC 2 Type II (in progress)
  • Security criteria met
  • Availability criteria met
  • Confidentiality criteria met
  • Processing integrity under review
  • Privacy criteria under review
```

### 🎤 **Speaker Script**

Our security framework implements defense in depth across five layers.

Layer One handles authentication.

OAuth two point zero and O I D C integration provides modern identity management.

SAML two point zero S S O enables single sign on across CAL FIRE systems.

Multi factor authentication uses T O T P based verification for enhanced security.

J W T token based sessions maintain stateless authentication.

Session timeout is twenty four hours with automatic refresh for active users.

Password policy requires twelve plus characters with complexity requirements.


Layer Two manages authorization.

Role based access control or R B A C… assigns permissions based on job function.

Attribute based access control or A B A C… adds context aware permission decisions.

Least privilege principle ensures users receive only necessary access.

Permission inheritance and delegation simplify management of complex hierarchies.

Temporary access grants with expiration support contractor and partner access.

Emergency override procedures enable rapid response while maintaining complete audit trails.


Layer Three protects data.

Encryption at rest uses A E S two fifty six for all stored data.

Encryption in transit uses T L S one point three for all network communication.

Key management leverages AWS K M S or HashiCorp Vault.

Data masking protects sensitive fields during display and export.

Row level security policies restrict access based on user attributes.

Column level encryption provides additional protection for personally identifiable information.


Layer Four provides audit and monitoring.

Comprehensive audit logging captures all user actions.

Real time anomaly detection identifies unusual patterns.

Security event correlation links related activities.

Automated alert generation notifies security teams of threats.

Forensic investigation tools enable post incident analysis.

And compliance reporting demonstrates regulatory adherence.


Layer Five secures the network perimeter.

A P I gateway rate limiting prevents abuse at one thousand requests per hour per user.

D DoS protection defends against denial of service attacks.

Web application firewall or WAF… blocks common attack patterns.

I P whitelisting and blacklisting control source address access.

V P N is required for all external access.

Network segmentation separates D M Z… internal… and data zones.


Five security policies govern our implementation.

Data classification defines five levels.

PUBLIC covers weather data and historical information.

INTERNAL includes fire incidents and operational reports.

RESTRICTED protects predictive models and A I outputs.

CONFIDENTIAL secures emergency response data.

SECRET safeguards critical infrastructure information.


Access level mapping ties classification to minimum required roles.

PUBLIC data requires viewer role.

INTERNAL requires analyst role.

RESTRICTED requires data scientist role.

CONFIDENTIAL requires fire chief role.

SECRET requires system admin role.


Data retention policies meet compliance requirements.

Fire data is retained for seven years per FISMA requirements.

Weather data is kept for three years.

Audit logs are maintained for seven years for compliance.

Temporary files and cache expire after twenty four hours.

Legal hold provides indefinite freeze when litigation is pending.


Encryption standards ensure comprehensive protection.

Data at rest uses A E S two fifty six G C M mode.

Data in transit uses T L S one point three.

Key rotation occurs every ninety days.

Key storage uses hardware security modules or AWS K M S.


Audit requirements maintain comprehensive accountability.

All data access is logged with user… timestamp… and resource details.

Failed login attempts are tracked for security analysis.

Configuration changes require approval and are logged.

Export activities are monitored for data loss prevention.

Anomalies trigger immediate security alerts.


Our real time security dashboard displays current health.

Security health score stands at ninety four out of one hundred… rated excellent.

Active sessions number two hundred forty seven.

Failed login attempts total three in the last twenty four hours.

Anomaly alerts are zero in the last twenty four hours.

Audit log entries reach twelve thousand eight hundred forty seven in the last twenty four hours.

Encryption coverage is one hundred percent.

Access policy violations total one… already investigated and resolved.


Security events from the last seven days show patterns.

Login events total two thousand eight hundred forty seven… rated low risk.

Data access events total eight thousand nine hundred thirty four… rated low risk.

Export events total one hundred fifty six… rated medium risk.

Configuration changes total twelve… rated high risk per policy.

Failed authentication attempts total forty seven… rated medium risk.

Anomaly events total two… rated high risk but fully investigated.


Recent high risk events demonstrate our monitoring effectiveness.

October nineteenth at fifteen forty seven… multiple failed login attempts from unknown user at I P one ninety two dot one sixty eight dot five dot two thirty four.

Actions taken include I P blacklisted and security team notified.

October eighteenth at twenty two fifteen… after hours data export of confidential reports by analyst zero zero five.

Actions taken include reviewed and authorized by supervisor.


We align with major compliance frameworks.

FISMA or Federal Information Security Management Act… compliance includes completed risk assessment… documented security controls… continuous monitoring enabled… and active incident response plan.

NIST eight hundred fifty three Security and Privacy Controls implementation covers Access Control family with eighteen controls… Audit and Accountability family with twelve controls… Identification and Authentication family with eleven controls… and System and Communications Protection family with fifteen controls.

HIPAA compliance if health data is processed… includes Privacy Rule compliance… Security Rule compliance… and breach notification procedures.

California Consumer Privacy Act or CCPA… compliance maintains data inventory… implements consent management… provides right to deletion procedures… and delivers privacy notices.

SOC two Type Two certification is in progress… with security criteria met… availability criteria met… confidentiality criteria met… processing integrity under review… and privacy criteria under review.


This comprehensive security framework protects wildfire intelligence data at every layer… ensuring confidentiality… integrity… and availability while maintaining compliance with all applicable regulations.

---

Due to length constraints, I'll create a separate file with the remaining slides. Let me continue with slides 17-36.
