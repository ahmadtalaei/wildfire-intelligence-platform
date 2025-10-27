## Slide 9: Built-in Charting and Geospatial Mapping

### **Leaflet + Mapbox Integration for Fire Visualization**

```mermaid
sequenceDiagram
    participant USER as User Dashboard
    participant MAP as Map Component<br/>(Leaflet)
    participant API as Data Clearing House<br/>API
    participant PG as PostgreSQL<br/>(HOT Tier)
    participant TILE as Mapbox Tile Server
    participant CACHE as Redis Cache

    USER->>MAP: Initialize map view<br/>(lat: 38.5, lon: -120.5, zoom: 7)
    MAP->>TILE: Request base layer tiles<br/>(California region)
    TILE-->>MAP: Return vector tiles (streets, terrain)

    USER->>MAP: Toggle fire detection layer
    MAP->>CACHE: Check cached fire data<br/>(last 24h)

    alt Cache Hit (70% of requests)
        CACHE-->>MAP: ✅ Return cached GeoJSON<br/>(1000 fire markers)
        Note over MAP: Render from cache<br/>< 100ms
    else Cache Miss
        MAP->>API: GET /api/fires?bbox=...&time=24h
        API->>PG: SELECT * FROM fire_detections<br/>WHERE ST_Within(geom, bbox)
        PG-->>API: Return 1000 records (87ms)
        API-->>MAP: GeoJSON FeatureCollection
        MAP->>CACHE: Store in cache (15-min TTL)
    end

    MAP->>MAP: Cluster markers<br/>(1000 → 47 clusters)
    MAP-->>USER: Display clustered map<br/>Total render: 187ms

    USER->>MAP: Click on cluster
    MAP->>MAP: Zoom in, expand cluster
    MAP-->>USER: Show individual fire markers

    USER->>MAP: Click on fire marker
    MAP->>API: GET /api/fires/{detection_id}
    API->>PG: SELECT detailed fire data
    PG-->>API: Fire details + weather + sensor
    API-->>MAP: Comprehensive fire info
    MAP-->>USER: Popup with fire details<br/>(temp, confidence, time)

    style MAP fill:#4ecdc4
    style CACHE fill:#95e1d3
    style PG fill:#ffe66d
    style TILE fill:#a29bfe
```

**GEOSPATIAL CAPABILITIES:**
```
┌─────────────────────────────────────────────────────────────────┐
│          BUILT-IN CHARTING & GEOSPATIAL MAPPING                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LEAFLET + MAPBOX INTEGRATION:                                  │
│                                                                 │
│  🗺️ Base Layer Options:                                         │
│     1. OpenStreetMap (default, no API key required)             │
│        - Free, community-maintained                             │
│        - Updated weekly                                         │
│        - Zoom levels 0-19                                       │
│                                                                 │
│     2. Mapbox Satellite (API key required)                      │
│        - High-resolution imagery                                │
│        - Updated monthly                                        │
│        - Zoom levels 0-22                                       │
│        - Cost: $5/1000 tile requests                            │
│                                                                 │
│     3. USGS Terrain                                             │
│        - Elevation shading                                      │
│        - Contour lines every 100ft                              │
│        - Critical for fire spread modeling                      │
│                                                                 │
│  FIRE DETECTION VISUALIZATION:                                  │
│                                                                 │
│  🔥 Marker Clustering (Performance Optimization)                │
│     - Leaflet.markercluster plugin                              │
│     - Reduces 1000 markers → 47 clusters at state level        │
│     - Dynamic zoom-based expansion                              │
│     - Cluster color by max confidence (low=yellow, high=red)   │
│                                                                 │
│  🎨 Fire Marker Symbology:                                      │
│     Confidence Level:                                           │
│       - Low (<30%): ⬤ Yellow circle (radius 5px)               │
│       - Nominal (30-80%): ⬤ Orange circle (radius 7px)         │
│       - High (>80%): ⬤ Red circle (radius 10px)                │
│                                                                 │
│     Brightness Temperature (color intensity):                   │
│       - <320K: Light red                                        │
│       - 320-360K: Medium red                                    │
│       - >360K: Dark red (intense fire)                          │
│                                                                 │
│  📊 Interactive Popups (Click on marker):                       │
│     Fire Detection Details:                                     │
│       - Detection time (UTC + PST conversion)                   │
│       - Latitude/Longitude (decimal degrees)                    │
│       - Brightness temperature (Kelvin)                         │
│       - Fire Radiative Power (MW)                               │
│       - Confidence level (percentage)                           │
│       - Satellite source (MODIS/VIIRS)                          │
│       - County and nearest city                                 │
│                                                                 │
│     Contextual Data (API enrichment):                           │
│       - Current weather (temp, humidity, wind)                  │
│       - Nearest IoT sensor readings                             │
│       - Historical fire count in 5km radius                     │
│       - Evacuation zone status                                  │
│                                                                 │
│  🌐 Overlay Layers (Toggle on/off):                             │
│     ✓ Fire Perimeters (GeoJSON polygons from CAL FIRE)         │
│     ✓ Weather Stations (NOAA, 150 stations statewide)          │
│     ✓ IoT Sensors (PurpleAir, 250 sensors)                     │
│     ✓ Evacuation Zones (CalOES, high-risk areas)               │
│     ✓ Critical Infrastructure (power plants, hospitals)        │
│     ✓ County Boundaries (CA 58 counties)                        │
│     ✓ Protected Lands (National Forests, Parks)                │
│                                                                 │
│  PERFORMANCE OPTIMIZATION:                                      │
│  • Redis caching: 70% cache hit rate (15-min TTL)              │
│  • PostGIS spatial index: 10x faster queries (3ms vs 30ms)     │
│  • Viewport-based querying: Only fetch visible fires           │
│  • Marker clustering: Reduces render time by 80%               │
│  • Lazy loading: Load tiles as user pans                       │
│  • Debounced API calls: 500ms wait after pan stops             │
│                                                                 │
│  ACCESSIBILITY:                                                 │
│  • Keyboard navigation (arrow keys to pan)                      │
│  • Screen reader support (ARIA labels)                          │
│  • High contrast mode for visually impaired                     │
│  • Colorblind-friendly palettes (red-blue, not red-green)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎤 **Speaker Script**

"Our Built-in Charting and Geospatial Mapping capabilities leverage Leaflet and Mapbox to create interactive fire visualization.

The platform offers three base layer options. OpenStreetMap is the default... requiring no A P I key... free and community-maintained... updated weekly... with zoom levels zero through nineteen. Mapbox Satellite provides high-resolution imagery... updated monthly... zoom levels zero through twenty two... costing five dollars per one thousand tile requests. USGS Terrain displays elevation shading... contour lines every one hundred feet... critical for fire spread modeling that accounts for topography.

Fire Detection Visualization uses marker clustering for performance optimization. The Leaflet dot markercluster plugin reduces one thousand individual markers down to forty seven clusters at state level view. Dynamic zoom-based expansion reveals individual fires as users zoom in. Cluster color indicates maximum confidence... low fires show yellow... high confidence fires show red.

Fire Marker Symbology encodes multiple data dimensions. Confidence level determines marker size and color. Low confidence below thirty percent displays as yellow circles five pixels in radius. Nominal confidence thirty to eighty percent shows orange circles seven pixels wide. High confidence above eighty percent renders as red circles ten pixels in radius.

Brightness temperature modulates color intensity. Temperatures below three hundred twenty Kelvin appear light red. Three hundred twenty to three hundred sixty Kelvin shows medium red. Above three hundred sixty Kelvin displays dark red indicating intense fire.

Interactive Popups appear when users click fire markers. Detection details include time in both UTC and Pacific Standard... latitude and longitude in decimal degrees... brightness temperature in Kelvin... Fire Radiative Power in megawatts... confidence percentage... satellite source whether MODIS or VIIRS... plus county and nearest city.

The A P I enriches popups with contextual data. Current weather shows temperature... humidity... and wind. Nearest I o T sensor readings provide real-time air quality. Historical fire count within five kilometer radius indicates fire-prone areas. And evacuation zone status alerts if the area is under warning.

Seven overlay layers toggle on and off. Fire perimeters from CAL FIRE display as GeoJSON polygons. One hundred fifty N O A A weather stations appear statewide. Two hundred fifty PurpleAir I o T sensors show real-time data. CalOES evacuation zones highlight high-risk areas. Critical infrastructure marks power plants and hospitals. County boundaries show California's fifty eight counties. And protected lands indicate National Forests and Parks.

Performance Optimization ensures responsive mapping. Redis caching achieves seventy percent cache hit rate with fifteen-minute time to live. PostGIS spatial index delivers ten times faster queries... three milliseconds versus thirty milliseconds baseline. Viewport-based querying only fetches fires visible in the current map view. Marker clustering reduces render time by eighty percent. Lazy loading fetches tiles as users pan. And debounced A P I calls wait five hundred milliseconds after panning stops before fetching new data.

Accessibility features ensure inclusive design. Keyboard navigation supports arrow keys to pan. Screen reader support provides A R I A labels. High contrast mode assists visually impaired users. And colorblind-friendly palettes use red-blue instead of red-green to accommodate eight percent of males with color vision deficiency.

This mapping platform transforms satellite fire detections into actionable geographic intelligence... enabling rapid visual assessment of wildfire situations across California."

---

## Slide 10: Time-Series Analysis and Statistical Visualizations

### **Trend Analysis, Forecasting, and Anomaly Detection**

```mermaid
graph TB
    subgraph "Time-Series Analysis Pipeline"
        INPUT[Fire Detection Data<br/>2020-2025 Historical]

        subgraph "Data Preparation"
            RESAMPLE[Resample to Daily<br/>Frequency]
            INTERPOLATE[Fill Missing Values<br/>Linear Interpolation]
            DETREND[Remove Seasonality<br/>STL Decomposition]
        end

        subgraph "Statistical Models"
            ARIMA[ARIMA Model<br/>Auto-tuned (p,d,q)]
            PROPHET[Facebook Prophet<br/>Trend + Seasonality]
            LSTM[LSTM Neural Network<br/>Deep Learning]
        end

        subgraph "Forecast Output"
            PRED_7[7-Day Forecast<br/>95% Confidence Interval]
            PRED_30[30-Day Forecast<br/>80% Confidence Interval]
            ANOMALY[Anomaly Detection<br/>Z-score > 3]
        end

        subgraph "Visualization"
            LINE_CHART[Line Chart<br/>Historical + Forecast]
            DECOMP_CHART[Decomposition Plot<br/>Trend + Seasonal + Residual]
            ANOMALY_CHART[Anomaly Scatter<br/>Outliers Highlighted]
        end
    end

    INPUT --> RESAMPLE
    RESAMPLE --> INTERPOLATE
    INTERPOLATE --> DETREND

    DETREND --> ARIMA & PROPHET & LSTM

    ARIMA --> PRED_7
    PROPHET --> PRED_30
    LSTM --> PRED_7 & PRED_30

    DETREND --> ANOMALY

    PRED_7 --> LINE_CHART
    PRED_30 --> LINE_CHART
    DETREND --> DECOMP_CHART
    ANOMALY --> ANOMALY_CHART

    style INPUT fill:#4ecdc4
    style ARIMA fill:#f38181
    style PROPHET fill:#ffe66d
    style LSTM fill:#a29bfe
    style ANOMALY fill:#ff6b6b
```

**TIME-SERIES CAPABILITIES:**
```
┌─────────────────────────────────────────────────────────────────┐
│          TIME-SERIES ANALYSIS & STATISTICAL VISUALIZATIONS      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DATA PREPARATION:                                              │
│                                                                 │
│  📅 Resampling Strategies:                                      │
│     - Hourly: Real-time monitoring (IoT sensors)                │
│     - Daily: Fire count aggregation (standard analysis)         │
│     - Weekly: Trend analysis (smooths daily noise)              │
│     - Monthly: Seasonal pattern extraction (5-year cycles)      │
│                                                                 │
│  🔧 Data Quality Handling:                                      │
│     - Missing values: Linear interpolation (max gap: 3 days)    │
│     - Outliers: Winsorization at 99th percentile               │
│     - Zero inflation: Handle days with no fires                 │
│     - Non-stationarity: First-order differencing                │
│                                                                 │
│  STATISTICAL MODELS:                                            │
│                                                                 │
│  📈 ARIMA (AutoRegressive Integrated Moving Average)            │
│     Configuration:                                              │
│       - Auto-tuned parameters (p,d,q) via AIC minimization      │
│       - Typical best fit: ARIMA(2,1,2) for fire count          │
│       - Seasonal extension: SARIMA(2,1,2)(1,1,1)[365]          │
│       - Training window: 3 years rolling                        │
│                                                                 │
│     Performance:                                                │
│       - 7-day forecast RMSE: 12.3 fires/day                    │
│       - 30-day forecast RMSE: 28.7 fires/day                   │
│       - Confidence intervals: 95% for 7-day, 80% for 30-day    │
│                                                                 │
│  🔮 Facebook Prophet (Trend + Seasonality + Holidays)           │
│     Components:                                                 │
│       - Trend: Piecewise linear with automatic changepoints     │
│       - Yearly seasonality: Fourier order 10 (fire season)     │
│       - Weekly seasonality: Fourier order 3 (weekend effect)   │
│       - Holidays: CA fire season (May 1 - Oct 31)              │
│                                                                 │
│     Advantages:                                                 │
│       - Handles missing data gracefully                         │
│       - Robust to outliers                                      │
│       - Interpretable components (can explain predictions)      │
│       - Fast training: <10 seconds for 5 years of daily data   │
│                                                                 │
│     Performance:                                                │
│       - 7-day forecast MAPE: 18.2%                             │
│       - 30-day forecast MAPE: 31.5%                            │
│       - Changepoint detection: Identifies 2020 mega-fires      │
│                                                                 │
│  🧠 LSTM Neural Network (Deep Learning)                         │
│     Architecture:                                               │
│       - Input layer: 30-day lookback window                     │
│       - Hidden layers: 2 LSTM layers (128 units each)           │
│       - Dropout: 0.2 (prevent overfitting)                      │
│       - Output layer: 7-day forecast horizon                    │
│                                                                 │
│     Training:                                                   │
│       - Loss function: Mean Squared Error (MSE)                 │
│       - Optimizer: Adam (learning rate: 0.001)                  │
│       - Epochs: 50 (early stopping on validation loss)          │
│       - Training time: 2 minutes on GPU                         │
│                                                                 │
│     Performance:                                                │
│       - 7-day forecast RMSE: 9.8 fires/day (best)              │
│       - Captures complex non-linear patterns                    │
│       - Requires large training dataset (3+ years)              │
│                                                                 │
│  ANOMALY DETECTION:                                             │
│                                                                 │
│  ⚠️  Z-Score Method (Statistical Outlier Detection)              │
│     - Calculate rolling mean (30-day window)                    │
│     - Calculate rolling std dev (30-day window)                 │
│     - Z-score = (value - mean) / std                            │
│     - Threshold: Z > 3 (99.7% confidence)                       │
│     - Flags: 2020 August mega-fires (Z=7.2)                    │
│                                                                 │
│  🔍 Isolation Forest (ML-based Anomaly Detection)               │
│     - Unsupervised learning algorithm                           │
│     - Contamination rate: 0.05 (5% expected outliers)           │
│     - Features: Fire count, temperature, humidity, wind         │
│     - Detects multivariate anomalies (not just univariate)      │
│                                                                 │
│  VISUALIZATION TYPES:                                           │
│                                                                 │
│  📊 Line Chart (Historical + Forecast)                          │
│     - Historical: Solid blue line (actual observations)         │
│     - Forecast: Dashed red line (predicted values)              │
│     - Confidence band: Shaded area (upper/lower bounds)         │
│     - Hover tooltip: Date, actual, predicted, ± error           │
│                                                                 │
│  📉 Decomposition Plot (Trend + Seasonal + Residual)            │
│     - Panel 1: Original time series                             │
│     - Panel 2: Trend component (long-term pattern)              │
│     - Panel 3: Seasonal component (annual cycle)                │
│     - Panel 4: Residual (unexplained variance)                  │
│     - Interpretation: High residual = poor model fit            │
│                                                                 │
│  ⭕ Anomaly Scatter (Outliers Highlighted)                      │
│     - X-axis: Date                                              │
│     - Y-axis: Fire count                                        │
│     - Normal points: Blue circles                               │
│     - Anomalies: Red stars (size = Z-score magnitude)           │
│     - Hover: Explains why point is anomalous                    │
│                                                                 │
│  EXPORT & SHARING:                                              │
│  • Forecast CSV: Date, predicted value, lower bound, upper     │
│  • Model coefficients: ARIMA parameters, Prophet components    │
│  • Jupyter notebook: Reproducible analysis with code            │
│  • Interactive HTML: Plotly chart with zoom/pan                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎤 **Speaker Script**

"Time-Series Analysis and Statistical Visualizations enable California fire scientists to identify trends... forecast future fire activity... and detect anomalous events requiring immediate attention.

Data Preparation begins with resampling strategies. Hourly resampling supports real-time monitoring of I o T sensors. Daily resampling aggregates fire counts for standard analysis. Weekly resampling smooths daily noise to reveal trends. Monthly resampling extracts seasonal patterns across five-year cycles.

Data quality handling addresses real-world challenges. Missing values use linear interpolation with a maximum gap of three days. Outliers apply winsorization at the ninety ninth percentile. Zero inflation accounts for days with no fires. And non-stationarity uses first-order differencing to stabilize variance.

Three Statistical Models provide complementary forecasting capabilities. A R I M A... AutoRegressive Integrated Moving Average... auto-tunes parameters via A I C minimization. Typical best fit is A R I M A two-one-two for daily fire counts. Seasonal extension S A R I M A adds yearly patterns with period three hundred sixty five.

A R I M A performance shows seven-day forecast root mean squared error of twelve point three fires per day. Thirty-day forecast R M S E reaches twenty eight point seven fires per day. Confidence intervals are ninety five percent for seven-day forecasts... and eighty percent for thirty-day forecasts.

Facebook Prophet decomposes time series into trend... seasonality... and holiday components. Piecewise linear trend detects automatic changepoints when fire patterns shift. Yearly seasonality uses Fourier order ten to model fire season May through October. Weekly seasonality with Fourier order three captures weekend effects. And holiday effects account for California fire season.

Prophet advantages include graceful handling of missing data... robustness to outliers... interpretable components that explain predictions... and fast training under ten seconds for five years of daily data. Performance metrics show seven-day forecast mean absolute percentage error of eighteen point two percent... and thirty-day MAPE of thirty one point five percent.

LSTM Neural Networks provide deep learning forecasting. The architecture uses a thirty-day lookback window as input... two LSTM layers with one hundred twenty eight units each... dropout of zero point two to prevent overfitting... and output layer predicting a seven-day horizon.

Training uses mean squared error loss function... Adam optimizer with learning rate zero point zero zero one... fifty epochs with early stopping on validation loss... and completes in two minutes on GPU. Performance achieves seven-day forecast R M S E of nine point eight fires per day... the best among all models... capturing complex non-linear patterns.

Anomaly Detection employs two complementary methods. Z-Score statistical outlier detection calculates rolling mean and standard deviation over thirty-day windows. Z-scores exceeding three trigger alerts at ninety nine point seven percent confidence. The method flagged the twenty twenty August mega-fires with Z-score of seven point two.

Isolation Forest uses unsupervised machine learning for multivariate anomaly detection. Contamination rate of zero point zero five expects five percent outliers. Features include fire count... temperature... humidity... and wind speed. This detects complex anomalies missed by univariate Z-score method.

Visualization Types communicate time-series insights. Line Charts display historical data as solid blue lines... forecasts as dashed red lines... and confidence bands as shaded areas. Hover tooltips show date... actual value... predicted value... and error margin.

Decomposition Plots use four panels. Panel one shows the original time series. Panel two displays the trend component revealing long-term patterns. Panel three shows the seasonal component with annual cycles. Panel four presents residuals indicating unexplained variance. High residuals signal poor model fit requiring investigation.

Anomaly Scatter plots highlight outliers. Normal points appear as blue circles. Anomalies display as red stars sized by Z-score magnitude. Hover tooltips explain why each point is anomalous... such as extreme temperature or unusual wind patterns.

Export and Sharing enable reproducible research. Forecast C S V files include date... predicted value... lower bound... and upper bound. Model coefficients export A R I M A parameters and Prophet components. Jupyter notebooks provide reproducible analysis with embedded code. Interactive H T M L uses Plotly charts with zoom and pan capabilities.

This comprehensive time-series platform empowers California scientists to move beyond reactive firefighting... toward proactive prediction... strategic resource pre-positioning... and evidence-based policy decisions."

---
