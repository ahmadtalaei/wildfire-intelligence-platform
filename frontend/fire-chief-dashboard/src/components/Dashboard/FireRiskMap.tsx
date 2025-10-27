import React, { useEffect, useRef } from 'react';
import { Box, Typography, Chip } from '@mui/material';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-shadow.png',
});

interface FireRiskData {
  id: string;
  location: {
    latitude: number;
    longitude: number;
    name: string;
  };
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'extreme';
  timestamp: string;
}

interface ActiveIncident {
  id: string;
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  status: string;
  acresBurned: number;
  containment: number;
}

interface FireRiskMapProps {
  riskData: FireRiskData[];
  incidents: ActiveIncident[];
}

const FireRiskMap: React.FC<FireRiskMapProps> = ({ riskData, incidents }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    // Initialize map
    const map = L.map(mapRef.current).setView([37.5, -120.5], 6); // California center
    mapInstanceRef.current = map;

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '(C) OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current) return;

    const map = mapInstanceRef.current;

    // Clear existing layers (except base layer)
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Circle) {
        map.removeLayer(layer);
      }
    });

    // Add risk assessment circles
    riskData.forEach((risk) => {
      const { latitude, longitude } = risk.location;
      
      let color: string;
      let radius: number;
      
      switch (risk.riskLevel) {
        case 'extreme':
          color = '#d32f2f';
          radius = 8000;
          break;
        case 'high':
          color = '#ff6b35';
          radius = 6000;
          break;
        case 'medium':
          color = '#ffab00';
          radius = 4000;
          break;
        case 'low':
          color = '#4caf50';
          radius = 2000;
          break;
        default:
          color = '#9e9e9e';
          radius = 2000;
      }

      const circle = L.circle([latitude, longitude], {
        color: color,
        fillColor: color,
        fillOpacity: 0.3,
        radius: radius,
      }).addTo(map);

      circle.bindPopup(`
        <div>
          <strong>${risk.location.name}</strong><br/>
          Risk Level: <span style="color: ${color}; font-weight: bold;">${risk.riskLevel.toUpperCase()}</span><br/>
          Risk Score: ${(risk.riskScore * 100).toFixed(1)}%<br/>
          <small>Updated: ${new Date(risk.timestamp).toLocaleString()}</small>
        </div>
      `);
    });

    // Add active incident markers
    incidents.forEach((incident) => {
      const { latitude, longitude } = incident.location;
      
      // Create custom fire icon
      const fireIcon = L.divIcon({
        html: `<div style="
          background-color: #d32f2f;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 2px solid white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: white;
          font-weight: bold;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        ">[FIRE]</div>`,
        className: 'fire-incident-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([latitude, longitude], { icon: fireIcon }).addTo(map);

      marker.bindPopup(`
        <div>
          <strong>${incident.name}</strong><br/>
          Status: <span style="font-weight: bold;">${incident.status.toUpperCase()}</span><br/>
          Acres Burned: ${incident.acresBurned.toLocaleString()}<br/>
          Containment: ${incident.containment}%<br/>
        </div>
      `);
    });

  }, [riskData, incidents]);

  return (
    <Box sx={{ position: 'relative', height: '100%' }}>
      <div
        ref={mapRef}
        style={{
          height: '400px',
          width: '100%',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
      />
      
      {/* Legend */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          p: 2,
          borderRadius: 2,
          boxShadow: 1,
          minWidth: 200,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Fire Risk Levels
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                backgroundColor: '#4caf50',
                opacity: 0.7,
              }}
            />
            <Typography variant="caption">Low Risk</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                backgroundColor: '#ffab00',
                opacity: 0.7,
              }}
            />
            <Typography variant="caption">Medium Risk</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                backgroundColor: '#ff6b35',
                opacity: 0.7,
              }}
            />
            <Typography variant="caption">High Risk</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                backgroundColor: '#d32f2f',
                opacity: 0.7,
              }}
            />
            <Typography variant="caption">Extreme Risk</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                backgroundColor: '#d32f2f',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '8px',
              }}
            >
              [FIRE]
            </Box>
            <Typography variant="caption">Active Incidents</Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default FireRiskMap;