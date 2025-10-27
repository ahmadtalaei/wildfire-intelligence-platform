# California Fire Data Loader - PowerShell Script
# Loads historical California fire data into the Wildfire Intelligence Platform

param(
    [int]$Count = 20,
    [int]$Year = 2023,
    [switch]$HistoricalOnly,
    [switch]$WithWeather,
    [string]$ApiBase = "http://localhost:8001"
)

# Major California Fires Data
$MajorFires = @(
    @{
        Name = "Camp Fire"
        Year = 2018
        Date = "2018-11-08T06:30:00Z"
        Latitude = 39.7596
        Longitude = -121.6219
        Confidence = 0.95
        Temperature = 850.0
        Source = "Camp_Fire_2018"
    },
    @{
        Name = "Thomas Fire"
        Year = 2017
        Date = "2017-12-04T18:45:00Z"
        Latitude = 34.4208
        Longitude = -119.1391
        Confidence = 0.92
        Temperature = 780.0
        Source = "Thomas_Fire_2017"
    },
    @{
        Name = "Tubbs Fire"
        Year = 2017
        Date = "2017-10-08T21:00:00Z"
        Latitude = 38.5125
        Longitude = -122.5572
        Confidence = 0.89
        Temperature = 720.0
        Source = "Tubbs_Fire_2017"
    },
    @{
        Name = "Woolsey Fire"
        Year = 2018
        Date = "2018-11-08T14:24:00Z"
        Latitude = 34.0259
        Longitude = -118.7798
        Confidence = 0.88
        Temperature = 760.0
        Source = "Woolsey_Fire_2018"
    },
    @{
        Name = "Dixie Fire"
        Year = 2021
        Date = "2021-07-13T17:00:00Z"
        Latitude = 40.0171
        Longitude = -121.0186
        Confidence = 0.94
        Temperature = 830.0
        Source = "Dixie_Fire_2021"
    }
)

# Fire zones for synthetic data
$FireZones = @(
    @{ Name = "Los Angeles"; LatMin = 34.0; LatMax = 34.8; LonMin = -118.7; LonMax = -117.6 },
    @{ Name = "Orange County"; LatMin = 33.4; LatMax = 33.9; LonMin = -118.0; LonMax = -117.4 },
    @{ Name = "Napa Valley"; LatMin = 38.2; LatMax = 38.9; LonMin = -122.8; LonMax = -122.0 },
    @{ Name = "Sonoma County"; LatMin = 38.1; LatMax = 38.9; LonMin = -123.5; LonMax = -122.3 }
)

function Test-ApiConnection {
    param([string]$BaseUrl)
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5
        return $true
    }
    catch {
        return $false
    }
}

function Add-FireIncident {
    param(
        [hashtable]$FireData,
        [string]$BaseUrl
    )
    
    $body = @{
        latitude = $FireData.Latitude
        longitude = $FireData.Longitude
        confidence = $FireData.Confidence
        temperature = $FireData.Temperature
        source = $FireData.Source
        timestamp = $FireData.Date
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/fires" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
        Write-Host "[CHECK] Loaded: $($FireData.Name) - ID: $($response.incident_id)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[X] Failed to load $($FireData.Name): $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function New-SyntheticFire {
    param(
        [hashtable]$Zone,
        [int]$Year
    )
    
    $randomLat = [math]::Round((Get-Random -Minimum $Zone.LatMin -Maximum $Zone.LatMax), 6)
    $randomLon = [math]::Round((Get-Random -Minimum $Zone.LonMin -Maximum $Zone.LonMax), 6)
    $randomConf = [math]::Round((Get-Random -Minimum 0.65 -Maximum 0.98), 2)
    $randomTemp = [math]::Round((Get-Random -Minimum 580.0 -Maximum 900.0), 1)
    
    # Random date in fire season (May-October)
    $fireSeasonStart = Get-Date -Year $Year -Month 5 -Day 1
    $fireSeasonEnd = Get-Date -Year $Year -Month 10 -Day 31
    $randomDays = Get-Random -Minimum 0 -Maximum (($fireSeasonEnd - $fireSeasonStart).Days)
    $randomDate = $fireSeasonStart.AddDays($randomDays).ToString("yyyy-MM-ddTHH:mm:ssZ")
    
    return @{
        Name = "Synthetic_$($Zone.Name)_$(Get-Random -Minimum 1000 -Maximum 9999)"
        Date = $randomDate
        Latitude = $randomLat
        Longitude = $randomLon
        Confidence = $randomConf
        Temperature = $randomTemp
        Source = "synthetic_$($Year)_fire_season"
    }
}

function Get-DatabaseStats {
    param([string]$BaseUrl)
    
    try {
        $stats = Invoke-RestMethod -Uri "$BaseUrl/api/v1/stats" -Method Get -TimeoutSec 5
        return $stats.statistics
    }
    catch {
        return @{}
    }
}

# Main execution
Write-Host "=" * 60 -ForegroundColor Yellow
Write-Host "[FIRE] California Fire Data Loader - PowerShell [FIRE]" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Yellow

# Check API connection
Write-Host "`n[MAGNIFYING_GLASS] Checking API connection..." -ForegroundColor Cyan
if (-not (Test-ApiConnection -BaseUrl $ApiBase)) {
    Write-Host "[X] Error: Cannot connect to API at $ApiBase" -ForegroundColor Red
    Write-Host "Make sure the platform is running:" -ForegroundColor Yellow
    Write-Host "docker-compose -f docker-compose-simple.yml up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "[CHECK] API connection successful" -ForegroundColor Green

# Get initial stats
$initialStats = Get-DatabaseStats -BaseUrl $ApiBase
$initialFires = $initialStats.fire_incidents ?? 0
Write-Host "`n[BAR_CHART] Current database: $initialFires fire incidents" -ForegroundColor Cyan

# Load historical fires
Write-Host "`n[BOOKS] Loading $($MajorFires.Count) major historical fires..." -ForegroundColor Cyan
$historicalLoaded = 0

foreach ($fire in $MajorFires) {
    if (Add-FireIncident -FireData $fire -BaseUrl $ApiBase) {
        $historicalLoaded++
    }
    Start-Sleep -Milliseconds 100
}

# Load synthetic data
$syntheticLoaded = 0
if (-not $HistoricalOnly -and $Count -gt 0) {
    Write-Host "`n[DART] Generating $Count synthetic fires for $Year..." -ForegroundColor Cyan
    
    for ($i = 1; $i -le $Count; $i++) {
        $zone = $FireZones | Get-Random
        $syntheticFire = New-SyntheticFire -Zone $zone -Year $Year
        
        if (Add-FireIncident -FireData $syntheticFire -BaseUrl $ApiBase) {
            $syntheticLoaded++
        }
        
        if ($i % 10 -eq 0) {
            Write-Host "   Generated $i/$Count synthetic fires..." -ForegroundColor Gray
        }
        
        Start-Sleep -Milliseconds 50
    }
}

# Final stats
Write-Host "`n" + ("=" * 60) -ForegroundColor Yellow
Write-Host "[CHECK] Data loading complete!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Yellow

$finalStats = Get-DatabaseStats -BaseUrl $ApiBase
$finalFires = $finalStats.fire_incidents ?? 0

Write-Host "`n[BAR_CHART] Historical fires loaded: $historicalLoaded" -ForegroundColor Cyan
Write-Host "[BAR_CHART] Synthetic fires loaded: $syntheticLoaded" -ForegroundColor Cyan
Write-Host "[BAR_CHART] Total new fires: $($historicalLoaded + $syntheticLoaded)" -ForegroundColor Cyan
Write-Host "[BAR_CHART] Total in database: $finalFires" -ForegroundColor Cyan

Write-Host "`n[GLOBE] View your data:" -ForegroundColor Yellow
Write-Host "   API: $ApiBase/api/v1/fires" -ForegroundColor Gray
Write-Host "   Stats: $ApiBase/api/v1/stats" -ForegroundColor Gray
Write-Host "   API Docs: $ApiBase/docs" -ForegroundColor Gray