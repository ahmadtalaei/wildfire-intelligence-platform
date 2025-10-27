"""
CNN Satellite Image Analysis for Fire Detection and Risk Assessment
Analyzes satellite imagery for fire detection, smoke plumes, and vegetation stress
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List, Optional, Tuple
import structlog
from datetime import datetime

logger = structlog.get_logger()


class FireDetectionCNN(nn.Module):
    """
    Convolutional Neural Network for satellite image fire detection

    Analyzes multi-spectral satellite imagery:
    - Visible (RGB)
    - Near-infrared (NIR)
    - Short-wave infrared (SWIR)
    - Thermal (TIR)

    Outputs:
    - Fire probability heatmap
    - Smoke detection
    - Vegetation stress index
    """

    def __init__(
        self,
        in_channels: int = 7,  # RGB + NIR + SWIR + TIR channels
        num_classes: int = 4   # Background, Active Fire, Smoke, Vegetation Stress
    ):
        super(FireDetectionCNN, self).__init__()

        # Encoder (downsampling)
        self.enc1 = self._conv_block(in_channels, 64)
        self.enc2 = self._conv_block(64, 128)
        self.enc3 = self._conv_block(128, 256)
        self.enc4 = self._conv_block(256, 512)

        # Decoder (upsampling)
        self.dec1 = self._upconv_block(512, 256)
        self.dec2 = self._upconv_block(512, 128)  # 512 = 256 + 256 (skip connection)
        self.dec3 = self._upconv_block(256, 64)
        self.dec4 = self._upconv_block(128, 32)

        # Output layers
        self.out_fire = nn.Conv2d(32, 1, kernel_size=1)  # Fire probability
        self.out_smoke = nn.Conv2d(32, 1, kernel_size=1)  # Smoke probability
        self.out_stress = nn.Conv2d(32, 1, kernel_size=1)  # Vegetation stress

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

    def _conv_block(self, in_channels: int, out_channels: int) -> nn.Module:
        """Convolutional block with batch norm and ReLU"""
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def _upconv_block(self, in_channels: int, out_channels: int) -> nn.Module:
        """Upsampling block with transpose convolution"""
        return nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass

        Args:
            x: Input tensor of shape (batch_size, channels, height, width)

        Returns:
            Dictionary with fire, smoke, and stress probability maps
        """
        # Encoder
        enc1 = self.enc1(x)
        enc2 = self.enc2(self.pool(enc1))
        enc3 = self.enc3(self.pool(enc2))
        enc4 = self.enc4(self.pool(enc3))

        # Decoder with skip connections
        dec1 = self.dec1(enc4)
        dec2 = self.dec2(torch.cat([dec1, enc3], dim=1))
        dec3 = self.dec3(torch.cat([dec2, enc2], dim=1))
        dec4 = self.dec4(torch.cat([dec3, enc1], dim=1))

        # Output heads
        fire_prob = torch.sigmoid(self.out_fire(dec4))
        smoke_prob = torch.sigmoid(self.out_smoke(dec4))
        stress_prob = torch.sigmoid(self.out_stress(dec4))

        return {
            "fire": fire_prob,
            "smoke": smoke_prob,
            "vegetation_stress": stress_prob
        }


class SatelliteImageAnalyzer:
    """
    Satellite image analysis engine for fire detection

    Manages model loading, preprocessing, and inference on satellite imagery
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu"
    ):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        # Initialize model
        self.model = FireDetectionCNN(
            in_channels=7,
            num_classes=4
        ).to(self.device)

        # Load pre-trained weights if available
        if model_path:
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                logger.info("CNN satellite model loaded", path=model_path)
            except Exception as e:
                logger.warning("Failed to load CNN model, using untrained model", error=str(e))

        # Channel normalization parameters (from training data statistics)
        self.channel_means = [0.3, 0.3, 0.3, 0.4, 0.3, 0.3, 300.0]  # RGB, NIR, SWIR, SWIR, TIR
        self.channel_stds = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 50.0]

    def preprocess_image(
        self,
        image_data: np.ndarray
    ) -> torch.Tensor:
        """
        Preprocess satellite image for model input

        Args:
            image_data: NumPy array of shape (height, width, channels)

        Returns:
            Preprocessed tensor
        """
        # Normalize channels
        normalized = np.zeros_like(image_data, dtype=np.float32)
        for i in range(image_data.shape[2]):
            normalized[:, :, i] = (image_data[:, :, i] - self.channel_means[i]) / self.channel_stds[i]

        # Convert to torch tensor and reorder dimensions (H, W, C) -> (C, H, W)
        tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0)  # Add batch dimension

        return tensor.to(self.device)

    def analyze(
        self,
        image_data: np.ndarray,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Analyze satellite image for fire, smoke, and vegetation stress

        Args:
            image_data: Multi-spectral satellite image (H, W, C)
            threshold: Detection threshold (0-1)

        Returns:
            Analysis results dictionary
        """
        try:
            # Preprocess
            input_tensor = self.preprocess_image(image_data)

            # Run inference
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(input_tensor)

            # Convert to numpy
            fire_map = outputs["fire"].cpu().numpy()[0, 0]
            smoke_map = outputs["smoke"].cpu().numpy()[0, 0]
            stress_map = outputs["vegetation_stress"].cpu().numpy()[0, 0]

            # Detect active fires
            fire_pixels = np.where(fire_map > threshold)
            fire_count = len(fire_pixels[0])

            # Calculate statistics
            fire_score = float(np.max(fire_map))
            fire_area_ratio = float(np.sum(fire_map > threshold) / fire_map.size)

            smoke_score = float(np.max(smoke_map))
            smoke_area_ratio = float(np.sum(smoke_map > threshold) / smoke_map.size)

            stress_score = float(np.mean(stress_map))

            # Detect fire hotspots (clusters of high probability pixels)
            hotspots = self._detect_hotspots(fire_map, threshold)

            result = {
                "model": "cnn_satellite_analyzer",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "image_dimensions": {
                    "height": image_data.shape[0],
                    "width": image_data.shape[1],
                    "channels": image_data.shape[2]
                },
                "fire_detection": {
                    "max_probability": fire_score,
                    "area_ratio": fire_area_ratio,
                    "pixel_count": fire_count,
                    "hotspots": hotspots
                },
                "smoke_detection": {
                    "max_probability": smoke_score,
                    "area_ratio": smoke_area_ratio
                },
                "vegetation_stress": {
                    "average_stress": stress_score,
                    "high_stress_ratio": float(np.sum(stress_map > 0.7) / stress_map.size)
                },
                "overall_risk": self._calculate_overall_risk(
                    fire_score, smoke_score, stress_score
                )
            }

            logger.info("Satellite image analysis completed",
                       fire_score=fire_score,
                       smoke_score=smoke_score,
                       hotspots=len(hotspots))

            return result

        except Exception as e:
            logger.error("Satellite image analysis failed", error=str(e))
            raise

    def _detect_hotspots(
        self,
        fire_map: np.ndarray,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Detect fire hotspot clusters

        Args:
            fire_map: Fire probability map
            threshold: Detection threshold

        Returns:
            List of hotspot dictionaries
        """
        from scipy.ndimage import label

        # Binary mask of high-probability pixels
        binary_mask = fire_map > threshold

        # Label connected components
        labeled, num_features = label(binary_mask)

        hotspots = []
        for i in range(1, num_features + 1):
            # Get pixels for this hotspot
            hotspot_pixels = np.where(labeled == i)

            # Calculate centroid
            center_y = int(np.mean(hotspot_pixels[0]))
            center_x = int(np.mean(hotspot_pixels[1]))

            # Calculate average probability
            avg_prob = float(np.mean(fire_map[hotspot_pixels]))

            # Pixel count
            pixel_count = len(hotspot_pixels[0])

            hotspots.append({
                "id": i,
                "center_pixel": {"y": center_y, "x": center_x},
                "pixel_count": pixel_count,
                "average_probability": avg_prob
            })

        # Sort by probability
        hotspots.sort(key=lambda h: h["average_probability"], reverse=True)

        return hotspots

    def _calculate_overall_risk(
        self,
        fire_score: float,
        smoke_score: float,
        stress_score: float
    ) -> Dict[str, Any]:
        """Calculate overall fire risk from all indicators"""
        # Weighted combination
        overall_score = (
            0.6 * fire_score +
            0.2 * smoke_score +
            0.2 * stress_score
        )

        risk_level = "low"
        if overall_score > 0.8:
            risk_level = "extreme"
        elif overall_score > 0.5:
            risk_level = "high"
        elif overall_score > 0.2:
            risk_level = "medium"

        return {
            "score": float(overall_score),
            "level": risk_level,
            "confidence": 0.85  # Model confidence (would be learned)
        }
