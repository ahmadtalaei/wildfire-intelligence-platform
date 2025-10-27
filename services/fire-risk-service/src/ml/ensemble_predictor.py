"""
Ensemble Fire Risk Prediction Model
Combines multiple ML models with weighted voting for robust predictions
"""

import numpy as np
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger()


class EnsembleFirePredictor:
    """
    Ensemble predictor combining multiple model types:
    - Random Forest (baseline)
    - LSTM Temporal (time-series patterns)
    - CNN Satellite (image analysis)
    - XGBoost (gradient boosting)
    - FireSat Data Source (real-time satellite detections)

    Uses weighted voting with dynamic confidence-based weights
    """

    def __init__(
        self,
        lstm_predictor=None,
        cnn_analyzer=None,
        baseline_model=None,
        firesat_source=None
    ):
        self.lstm_predictor = lstm_predictor
        self.cnn_analyzer = cnn_analyzer
        self.baseline_model = baseline_model
        self.firesat_source = firesat_source

        # Base weights (can be adjusted based on validation performance)
        self.model_weights = {
            "baseline": 0.20,      # Random Forest baseline
            "lstm_temporal": 0.25,  # LSTM for temporal patterns
            "cnn_satellite": 0.20,  # CNN for satellite imagery
            "firesat_realtime": 0.35  # Real-time FireSat detections (highest weight)
        }

    async def predict_ensemble(
        self,
        location: Dict[str, float],
        features: Dict[str, Any],
        time_series_data: Optional[List[Dict[str, Any]]] = None,
        satellite_image: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generate ensemble fire risk prediction

        Args:
            location: Dict with latitude, longitude
            features: Feature dictionary for baseline model
            time_series_data: Historical time series for LSTM
            satellite_image: Satellite imagery for CNN

        Returns:
            Ensemble prediction result
        """
        predictions = {}
        confidences = {}
        model_results = {}

        # 1. Baseline Random Forest prediction
        if self.baseline_model:
            try:
                baseline_pred = await self._predict_baseline(features)
                predictions["baseline"] = baseline_pred["risk_score"]
                confidences["baseline"] = baseline_pred.get("confidence", 0.7)
                model_results["baseline"] = baseline_pred
            except Exception as e:
                logger.warning("Baseline model prediction failed", error=str(e))

        # 2. LSTM temporal prediction
        if self.lstm_predictor and time_series_data:
            try:
                lstm_pred = self.lstm_predictor.predict(time_series_data)
                # Use average of 7-day forecast
                predictions["lstm_temporal"] = lstm_pred["average_risk"]
                confidences["lstm_temporal"] = lstm_pred.get("confidence", 0.75)
                model_results["lstm_temporal"] = lstm_pred
            except Exception as e:
                logger.warning("LSTM prediction failed", error=str(e))

        # 3. CNN satellite analysis
        if self.cnn_analyzer and satellite_image is not None:
            try:
                cnn_pred = self.cnn_analyzer.analyze(satellite_image)
                predictions["cnn_satellite"] = cnn_pred["overall_risk"]["score"]
                confidences["cnn_satellite"] = cnn_pred["overall_risk"].get("confidence", 0.85)
                model_results["cnn_satellite"] = cnn_pred
            except Exception as e:
                logger.warning("CNN satellite analysis failed", error=str(e))

        # 4. FireSat real-time detection
        if self.firesat_source:
            try:
                firesat_factors = await self.firesat_source.calculate_firesat_risk_factors(
                    location["latitude"],
                    location["longitude"]
                )

                # Convert FireSat factors to risk score
                firesat_risk = self._calculate_firesat_risk(firesat_factors)
                predictions["firesat_realtime"] = firesat_risk["risk_score"]
                confidences["firesat_realtime"] = firesat_risk.get("confidence", 0.90)
                model_results["firesat_realtime"] = firesat_factors
            except Exception as e:
                logger.warning("FireSat prediction failed", error=str(e))

        # Ensemble prediction using weighted voting
        ensemble_result = self._ensemble_vote(predictions, confidences)

        # Combine all results
        result = {
            "ensemble_prediction": ensemble_result,
            "individual_models": model_results,
            "model_agreement": self._calculate_model_agreement(predictions),
            "prediction_timestamp": datetime.utcnow().isoformat()
        }

        logger.info("Ensemble prediction completed",
                   ensemble_risk=ensemble_result["risk_score"],
                   ensemble_level=ensemble_result["risk_level"],
                   models_used=len(predictions))

        return result

    def _ensemble_vote(
        self,
        predictions: Dict[str, float],
        confidences: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Weighted voting with dynamic confidence adjustment

        Args:
            predictions: Model predictions (risk scores 0-1)
            confidences: Model confidence scores (0-1)

        Returns:
            Ensemble prediction result
        """
        if not predictions:
            return {
                "risk_score": 0.0,
                "risk_level": "unknown",
                "confidence": 0.0,
                "method": "ensemble_weighted_voting"
            }

        # Calculate confidence-adjusted weights
        total_weight = 0.0
        weighted_sum = 0.0

        for model_name, risk_score in predictions.items():
            base_weight = self.model_weights.get(model_name, 0.1)
            model_confidence = confidences.get(model_name, 0.5)

            # Adjust weight by confidence
            adjusted_weight = base_weight * model_confidence

            weighted_sum += risk_score * adjusted_weight
            total_weight += adjusted_weight

        # Calculate ensemble score
        ensemble_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Classify risk level
        risk_level = self._classify_risk_level(ensemble_score)

        # Calculate ensemble confidence (average of participating models)
        ensemble_confidence = np.mean(list(confidences.values())) if confidences else 0.0

        return {
            "risk_score": float(ensemble_score),
            "risk_level": risk_level,
            "confidence": float(ensemble_confidence),
            "models_used": len(predictions),
            "method": "ensemble_weighted_voting"
        }

    def _calculate_firesat_risk(self, firesat_factors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FireSat factors to unified risk score

        Args:
            firesat_factors: FireSat risk factors dictionary

        Returns:
            Risk score and metadata
        """
        # Weighted combination of FireSat factors
        proximity_risk = firesat_factors.get("proximity_risk_score", 0.0)
        spread_rate = min(firesat_factors.get("fire_spread_rate", 0.0) / 10.0, 1.0)  # Normalize
        max_frp = min(firesat_factors.get("max_frp", 0.0) / 100.0, 1.0)  # Normalize

        nearby_count = firesat_factors.get("nearby_fires_count", 0)
        count_factor = min(nearby_count / 10.0, 1.0)  # Normalize

        # Weighted combination
        risk_score = (
            0.4 * proximity_risk +
            0.3 * max_frp +
            0.2 * spread_rate +
            0.1 * count_factor
        )

        # Higher confidence when we have more detections
        confidence = 0.9 if nearby_count > 5 else 0.7 if nearby_count > 0 else 0.5

        return {
            "risk_score": float(risk_score),
            "confidence": confidence
        }

    def _calculate_model_agreement(self, predictions: Dict[str, float]) -> float:
        """
        Calculate agreement between models (inverse of standard deviation)

        Args:
            predictions: Model predictions

        Returns:
            Agreement score (0-1, higher = better agreement)
        """
        if len(predictions) < 2:
            return 1.0  # Perfect agreement with single model

        scores = list(predictions.values())
        std_dev = np.std(scores)

        # Convert std dev to agreement (0 std = 1.0 agreement)
        agreement = max(0.0, 1.0 - (std_dev / 0.5))  # Normalize by max expected std

        return float(agreement)

    def _classify_risk_level(self, risk_score: float) -> str:
        """Classify risk score into categorical level"""
        if risk_score < 0.2:
            return "low"
        elif risk_score < 0.5:
            return "medium"
        elif risk_score < 0.8:
            return "high"
        else:
            return "extreme"

    async def _predict_baseline(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Run baseline Random Forest prediction"""
        # This would use the existing FireRiskPredictor baseline model
        # Placeholder implementation
        return {
            "risk_score": 0.3,
            "confidence": 0.7,
            "model": "random_forest_baseline"
        }
