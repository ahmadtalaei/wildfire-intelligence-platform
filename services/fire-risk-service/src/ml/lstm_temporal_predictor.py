"""
LSTM Temporal Fire Prediction Model
Predicts fire risk using time-series weather and environmental data
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Tuple
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()


class LSTMFirePredictor(nn.Module):
    """
    LSTM-based temporal fire risk prediction model

    Processes time-series data including:
    - Weather patterns (temperature, humidity, wind, precipitation)
    - Vegetation indices over time
    - Historical fire occurrences
    - Seasonal patterns

    Predicts fire risk for next 1-7 days
    """

    def __init__(
        self,
        input_size: int = 20,
        hidden_size: int = 128,
        num_layers: int = 3,
        dropout: float = 0.2,
        forecast_horizon: int = 7
    ):
        super(LSTMFirePredictor, self).__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.forecast_horizon = forecast_horizon

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )

        # Attention mechanism
        self.attention = nn.Linear(hidden_size, 1)

        # Output layers
        self.fc1 = nn.Linear(hidden_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, forecast_horizon)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor, hidden: Optional[Tuple] = None) -> torch.Tensor:
        """
        Forward pass

        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            hidden: Optional hidden state tuple

        Returns:
            Fire risk predictions for forecast horizon
        """
        batch_size = x.size(0)

        # LSTM forward pass
        lstm_out, hidden = self.lstm(x, hidden)

        # Attention mechanism
        attention_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attention_weights * lstm_out, dim=1)

        # Fully connected layers
        out = self.relu(self.fc1(context))
        out = self.dropout(out)
        out = self.relu(self.fc2(out))
        out = self.dropout(out)
        out = self.fc3(out)

        # Sigmoid for probability output
        out = self.sigmoid(out)

        return out


class TemporalFireRiskPredictor:
    """
    Temporal fire risk prediction engine using LSTM

    Manages model loading, preprocessing, and inference
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu"
    ):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        # Initialize model
        self.model = LSTMFirePredictor(
            input_size=20,
            hidden_size=128,
            num_layers=3,
            dropout=0.2,
            forecast_horizon=7
        ).to(self.device)

        # Load pre-trained weights if available
        if model_path:
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                logger.info("LSTM model loaded", path=model_path)
            except Exception as e:
                logger.warning("Failed to load LSTM model, using untrained model", error=str(e))

        # Feature names and normalization parameters
        self.feature_names = [
            'temperature_c', 'relative_humidity', 'wind_speed', 'precipitation_mm',
            'ndvi', 'evi', 'fuel_moisture', 'drought_index',
            'fire_weather_index', 'temperature_humidity_index',
            'elevation_m', 'slope_degrees', 'aspect_degrees',
            'day_of_year_sin', 'day_of_year_cos',
            'nearby_fires_count', 'firesat_proximity_risk', 'firesat_max_frp',
            'historical_fire_frequency', 'fire_season_factor'
        ]

        # Normalization stats (would be loaded from training)
        self.feature_means = {name: 0.0 for name in self.feature_names}
        self.feature_stds = {name: 1.0 for name in self.feature_names}

    def prepare_sequence(
        self,
        time_series_data: List[Dict[str, Any]],
        sequence_length: int = 30
    ) -> torch.Tensor:
        """
        Prepare time series data for model input

        Args:
            time_series_data: List of feature dictionaries (chronological order)
            sequence_length: Number of time steps to use

        Returns:
            Normalized input tensor
        """
        # Ensure we have enough data
        if len(time_series_data) < sequence_length:
            # Pad with first observation if not enough data
            padding = [time_series_data[0]] * (sequence_length - len(time_series_data))
            time_series_data = padding + time_series_data

        # Take last sequence_length observations
        recent_data = time_series_data[-sequence_length:]

        # Extract and normalize features
        sequence = []
        for observation in recent_data:
            feature_vector = []
            for feature_name in self.feature_names:
                value = observation.get(feature_name, 0.0)

                # Normalize
                mean = self.feature_means.get(feature_name, 0.0)
                std = self.feature_stds.get(feature_name, 1.0)
                normalized_value = (value - mean) / (std + 1e-8)

                feature_vector.append(normalized_value)

            sequence.append(feature_vector)

        # Convert to tensor
        sequence_tensor = torch.tensor(sequence, dtype=torch.float32).unsqueeze(0)  # Add batch dimension

        return sequence_tensor.to(self.device)

    def predict(
        self,
        time_series_data: List[Dict[str, Any]],
        sequence_length: int = 30
    ) -> Dict[str, Any]:
        """
        Predict fire risk for next 7 days

        Args:
            time_series_data: Historical observations (chronological)
            sequence_length: Number of time steps to use

        Returns:
            Prediction dictionary with daily risk scores
        """
        try:
            # Prepare input
            input_tensor = self.prepare_sequence(time_series_data, sequence_length)

            # Run inference
            self.model.eval()
            with torch.no_grad():
                predictions = self.model(input_tensor)

            # Convert to numpy
            risk_scores = predictions.cpu().numpy()[0]

            # Create prediction results
            forecast_dates = [
                (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
                for i in range(len(risk_scores))
            ]

            daily_predictions = [
                {
                    "date": date,
                    "risk_score": float(score),
                    "risk_level": self._classify_risk(score)
                }
                for date, score in zip(forecast_dates, risk_scores)
            ]

            result = {
                "model": "lstm_temporal",
                "prediction_timestamp": datetime.utcnow().isoformat(),
                "forecast_horizon_days": len(risk_scores),
                "daily_predictions": daily_predictions,
                "average_risk": float(np.mean(risk_scores)),
                "max_risk": float(np.max(risk_scores)),
                "confidence": self._calculate_confidence(time_series_data)
            }

            logger.info("LSTM temporal prediction completed",
                       avg_risk=result["average_risk"],
                       max_risk=result["max_risk"])

            return result

        except Exception as e:
            logger.error("LSTM prediction failed", error=str(e))
            raise

    def _classify_risk(self, risk_score: float) -> str:
        """Classify risk score into categorical level"""
        if risk_score < 0.2:
            return "low"
        elif risk_score < 0.5:
            return "medium"
        elif risk_score < 0.8:
            return "high"
        else:
            return "extreme"

    def _calculate_confidence(self, time_series_data: List[Dict[str, Any]]) -> float:
        """Calculate prediction confidence based on data quality"""
        # More historical data = higher confidence
        data_completeness = min(len(time_series_data) / 30.0, 1.0)

        # Check for missing values
        missing_ratio = 0.0
        for observation in time_series_data[-7:]:  # Check recent week
            missing_count = sum(1 for name in self.feature_names if observation.get(name) is None)
            missing_ratio += missing_count / len(self.feature_names)

        missing_ratio /= min(len(time_series_data), 7)

        confidence = data_completeness * (1.0 - missing_ratio)

        return max(0.0, min(1.0, confidence))
