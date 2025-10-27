Welcome to the Wildfire Intelligence Operations Dashboard… a real-time monitoring system for tracking active fires across California using five NASA FIRMS satellites…


Before we dive into the dashboard… let me walk you through how to access this monitoring interface…

First… open your web browser and navigate to localhost port three thousand ten…

You will see the Grafana login page…

Enter the username… admin… all lowercase…

Then the password… also admin… all lowercase…

Click Sign In to access the Grafana dashboard interface.


Once logged in… you have two options to view the Wildfire Operations Dashboard…

Option one… if the dashboard is already imported… simply click on Dashboards in the left sidebar…

Then search for Wildfire Intelligence… or scroll through the list to find it…

Click on the dashboard name to open it.


Option two… if you need to import the dashboard from the JSON file…

Click the plus icon in the left sidebar… then select Import dashboard…

Click Upload JSON file… and browse to the file location…

Navigate to monitoring slash grafana slash dashboards slash wildfire dash overview dot json file…

Select the file and click Import… If the dashboard is already imported… Grafana may display an error stating… A dashboard or folder with the same name already exists…

Once imported successfully… Grafana will load the dashboard configuration… and you will see the Wildfire Intelligence Operations Dashboard appear.


This dashboard provides real-time visibility into active fire monitoring… showing live detections from five NASA satellites… with automatic deduplication to show actual fire locations… not just raw satellite observations…

The dashboard updates every thirty seconds… so you are seeing near real-time fire activity as data streams in from space.


Now… let us explore what this dashboard shows us…



At the top of the dashboard… we see three panels tracking confirmed fire incidents… These show only high-confidence detections… meaning fires with confidence levels greater than or equal to zero point eight… or eighty percent certainty…

These are fires that satellite algorithms have confirmed as actual burning… not just heat anomalies or false positives.


The first panel on the left shows Fire Incidents in the last twenty-four hours…

Currently… we are tracking three unique fire incidents detected in the past day…

This number updates in real time as satellites pass overhead and detect new fires… or as existing fires burn out.


The second panel displays Fire Incidents over the last seven days…

Right now… we see ten unique fire incidents over the past week…

On the right… the panel shows Total Fire Incidents over the last thirty days…

This panel currently displays thirty-three unique fire incidents over the past month…

This monthly count helps us track overall fire season intensity and activity trends.


All three panels use intelligent spatial-temporal deduplication with seven-day windows…

If five different satellites detect the same fire burning for three days… we count it as one incident… not multiple incidents…

But if a fire re-ignites at the same location after seven days… it counts as a new fire… because wildfires do not burn continuously in the same spot for weeks…

The algorithm rounds coordinates to one kilometer precision… ensuring we track actual fire locations, not inflated numbers from duplicate satellite observations.



Moving down to the second row… we see a different set of metrics… These panels show all satellite detections… regardless of confidence level…

This includes high-confidence fires… nominal detections… and low-confidence heat anomalies.


The first panel on the left shows Total Detections over the last twenty-four hours…

This panel displays two key numbers… Unique Locations and Total Observations…

This tells us that fifty-eight distinct fire-like locations were observed… but satellites made nearly nine thousand passes over those same locations… creating massive duplication.


The deduplication factor here is about one hundred sixty times… meaning each unique fire location was observed an average of one hundred sixty times in twenty-four hours.


In the center… the second panel displays Total Detections over the last seven days…

Similarly… this shows Unique Locations and Total Observations for the weekly time frame…

You might see two hundred fifty unique locations detected from about ninety-two thousand total observations…


On the right… the third panel shows Sensor Readings over the last seven days…

This provides an estimate of total sensor data points collected… combining all satellite instruments and ground-based IoT sensors.


The key insight from this row is understanding the difference between raw satellite observations and actual fire locations…

Without deduplication… we would be overwhelmed with hundreds of thousands of alerts… when in reality… there are only a few actual fires.



In the third row… we have two visualization panels that provide deeper insights into fire patterns and satellite coverage.


On the left… the Fire Activity Trends chart shows Unique Fires per Hour over the last seven days…

This is a time-series line graph… with the x-axis showing time in hourly intervals… and the y-axis showing the count of unique fire locations detected each hour.


Looking at the chart… you will notice peaks and valleys in fire activity…

For example… on October twenty-third at one p m… we see a peak of five unique fires detected in a single hour…

This represents a significant fire activity event… likely driven by weather conditions… wind patterns… or multiple simultaneous ignitions.


This chart uses the same deduplication algorithm… so the numbers represent actual distinct fire locations… not raw satellite detections…


On the right… the Data Sources Distribution table breaks down detections by satellite…

This table shows five rows… one for each NASA FIRMS satellite currently monitoring the region.


The first column lists the satellite names…

The second column shows Total Detections from each satellite over the selected time range…

For the last seven days… you might see numbers like nineteen thousand one hundred forty-nine detections from MODIS Terra… and similar counts from the other satellites.


The third column displays Average Confidence for each satellite…

Most satellites maintain an average confidence around zero point five… or about fifty percent… because they include all detections… not just high-confidence fires.


The fourth column shows High Confidence counts… which are detections with confidence greater than or equal to zero point eight…

For example… MODIS Terra might have about six hundred high-confidence detections out of nineteen thousand total… showing that only about three percent of raw detections are confirmed fires.


This table is valuable for understanding satellite coverage… reliability… and data quality…

If one satellite shows significantly lower detection counts… it might indicate a sensor malfunction… orbital issues… or cloud coverage blocking observations.



At the bottom of the dashboard… we have a comprehensive table showing all high-confidence fire detections…

Each row represents one unique fire location… sorted by Fire Radiative Power… with the most intense fires at the top.


The table includes several important columns…

Latitude and Longitude show the precise geographic coordinates… rounded to four decimal places for one hundred meter accuracy…

Confidence displays the average fire detection certainty score… with values above zero point eight… the eighty percent threshold.

Brightness in Kelvin shows the average temperature of the fire… with typical values ranging from three hundred to four hundred Kelvin for active fires…

Fire Radiative Power… or FRP… measured in Megawatts… shows the maximum intensity reading when multiple satellites observed the same fire… This is the primary sorting column… ensuring the most dangerous fires appear first.


The Satellites column shows which satellites detected each fire… such as N for NOAA-Twenty VIIRS… or A, T for Aqua and Terra MODIS…

Detections shows how many times each unique fire was observed by satellites… ranging from dozens to hundreds of observations for the same fire location.

Fire Time shows when the fire was first detected… in Pacific Time.


All column headers are clickable… allowing you to sort the table by any column alphabetically or numerically… in ascending or descending order…

By default… fires are sorted by FRP in descending order… so the most intense… dangerous fires appear at the top of the list.


This intelligent deduplication ensures that if five satellites detect the same fire… it appears as one row…

The table displays all unique fires within your selected time range… not limited to an arbitrary count…

This allows operators to see the complete fire situation at a glance… without being overwhelmed by duplicate satellite observations.


For example… a fire with an FRP of two hundred thirty-nine Megawatts is significantly more intense than one at ten Megawatts…

Fire chiefs can use this prioritization to allocate firefighting resources… aerial tankers… and ground crews to the highest-risk incidents first.


The table respects the time range selected in the dashboard time picker… allowing you to view fires from the last day… week… or any custom range.



In the top-right corner of the dashboard… you will see the time picker control…

By default… it shows Last seven days… but you can change this to any time range you need.


You can select Last thirty days for a monthly overview… Or select Last ninety days to analyze seasonal patterns.


For investigating a specific fire event… click Absolute time range to pick custom start and end dates…


When you change the time range… three key panels update automatically…

The Fire Activity Trends chart adjusts its hourly breakdown to your selected period…

The Data Sources Distribution table recalculates satellite detection counts for your timeframe…

The Recent Fire Incidents table filters to show only fires within your selected range…

This gives you tremendous flexibility to analyze historical fire data… compare time periods… or investigate specific fire events.



When a satellite detects a potential fire… the data flows through our ingestion pipeline…

First… it lands in Apache Kafka topics… where it is validated against Avro schemas to ensure data quality…

Then… our data storage service consumes the Kafka messages and inserts them into PostgreSQL tables… one table per satellite…

Finally… Grafana queries these tables every thirty seconds to refresh the dashboard.


The spatial-temporal deduplication happens at query time… using a smart seven-day window approach…

The algorithm identifies fires at the same location by rounding coordinates to approximately one kilometer precision… then groups them into seven-day windows…



This dashboard transforms raw satellite data into actionable wildfire intelligence for California emergency responders…


The system ingests tens of thousands of satellite observations daily… but only three to five percent are actual confirmed fires…

Our intelligent deduplication and high-confidence filtering… with the threshold set at eighty percent certainty… turning noisy satellite data into precise fire incident tracking.


Fire chiefs gain critical capabilities through this dashboard…

First… distinguish between actual fires and heat anomalies… avoiding wasted resources on false alarms…

Second… prioritize responses based on fire intensity… sending crews to the most dangerous fires first…

Third… track temporal patterns… pre-positioning resources before fire activity peaks driven by wind and weather conditions…

Fourth… monitor satellite coverage reliability… adjusting strategy if sensors go offline…

Fifth… investigate specific events… drilling down to exact location… timing… and intensity for any fire incident.

This represents the future of wildfire response infrastructure… faster detection… better resource allocation… saved lives… and protected property.
