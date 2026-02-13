"""
Battery Degradation Predictor
ML-based prediction of future battery health
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


@dataclass
class DegradationPrediction:
    """Prediction results for battery degradation"""
    current_soh: float
    predicted_soh_1year: float
    predicted_soh_2year: float
    predicted_soh_3year: float
    predicted_soh_5year: float
    
    # When will it reach thresholds
    years_to_80_percent: Optional[float]  # Warranty threshold
    years_to_70_percent: Optional[float]  # Replacement threshold
    
    # Degradation rate
    annual_degradation_rate: float  # % per year
    confidence: float
    
    # Recommendations
    optimal_replacement_year: Optional[int]
    estimated_remaining_value_chf: float


@dataclass
class HistoricalDataPoint:
    """Historical SoH measurement"""
    date: datetime
    soh_percent: float
    mileage_km: Optional[int] = None


class DegradationPredictor:
    """
    Predicts future battery degradation using multiple models.
    
    Models used:
    1. Linear regression on historical data
    2. Empirical degradation curves (NMC, LFP)
    3. Usage-pattern adjusted predictions
    
    Swiss market specific:
    - CHF value calculations
    - Swiss driving patterns (avg 12,000 km/year)
    - Swiss climate factors
    """
    
    # Swiss market constants
    AVG_ANNUAL_MILEAGE_KM = 12000
    BATTERY_VALUE_PER_KWH_CHF = 150
    
    # Degradation model parameters (based on research)
    # NMC batteries (Tesla, VW, etc.)
    NMC_CALENDAR_RATE = 0.02      # 2% per year
    NMC_CYCLE_RATE = 0.00015     # 0.015% per cycle
    
    # LFP batteries (Tesla SR+, BYD)
    LFP_CALENDAR_RATE = 0.015    # 1.5% per year
    LFP_CYCLE_RATE = 0.0001     # 0.01% per cycle
    
    def __init__(
        self,
        battery_type: str = "NMC",
        original_capacity_kwh: float = 60.0
    ):
        """
        Initialize predictor.
        
        Args:
            battery_type: "NMC" or "LFP"
            original_capacity_kwh: Original battery capacity
        """
        self.battery_type = battery_type.upper()
        self.original_capacity_kwh = original_capacity_kwh
        
        # Set degradation rates based on battery type
        if self.battery_type == "LFP":
            self.calendar_rate = self.LFP_CALENDAR_RATE
            self.cycle_rate = self.LFP_CYCLE_RATE
        else:
            self.calendar_rate = self.NMC_CALENDAR_RATE
            self.cycle_rate = self.NMC_CYCLE_RATE
    
    def predict(
        self,
        current_soh: float,
        vehicle_age_years: float,
        historical_data: Optional[List[HistoricalDataPoint]] = None,
        annual_mileage_km: int = None,
        fast_charge_ratio: float = 0.2
    ) -> DegradationPrediction:
        """
        Predict future battery degradation.
        
        Args:
            current_soh: Current State of Health (0-100)
            vehicle_age_years: Current age of vehicle
            historical_data: Optional historical SoH measurements
            annual_mileage_km: Expected annual mileage
            fast_charge_ratio: Ratio of fast charging (0-1)
            
        Returns:
            DegradationPrediction with future projections
        """
        annual_mileage = annual_mileage_km or self.AVG_ANNUAL_MILEAGE_KM
        
        # Calculate annual degradation rate
        if historical_data and len(historical_data) >= 2:
            annual_rate = self._calculate_rate_from_history(historical_data)
            confidence = min(0.9, 0.5 + len(historical_data) * 0.1)
        else:
            annual_rate = self._calculate_empirical_rate(
                annual_mileage, fast_charge_ratio
            )
            confidence = 0.6
        
        # Predict future SoH
        soh_1y = max(0, current_soh - annual_rate)
        soh_2y = max(0, current_soh - annual_rate * 2)
        soh_3y = max(0, current_soh - annual_rate * 3)
        soh_5y = max(0, current_soh - annual_rate * 5)
        
        # Calculate years to thresholds
        years_to_80 = self._years_to_threshold(current_soh, 80, annual_rate)
        years_to_70 = self._years_to_threshold(current_soh, 70, annual_rate)
        
        # Calculate remaining value
        remaining_capacity = self.original_capacity_kwh * (current_soh / 100)
        remaining_value = remaining_capacity * self.BATTERY_VALUE_PER_KWH_CHF
        
        # Optimal replacement year
        optimal_replacement = None
        if years_to_70:
            optimal_replacement = int(datetime.now().year + years_to_70)
        
        return DegradationPrediction(
            current_soh=round(current_soh, 1),
            predicted_soh_1year=round(soh_1y, 1),
            predicted_soh_2year=round(soh_2y, 1),
            predicted_soh_3year=round(soh_3y, 1),
            predicted_soh_5year=round(soh_5y, 1),
            years_to_80_percent=round(years_to_80, 1) if years_to_80 else None,
            years_to_70_percent=round(years_to_70, 1) if years_to_70 else None,
            annual_degradation_rate=round(annual_rate, 2),
            confidence=round(confidence, 2),
            optimal_replacement_year=optimal_replacement,
            estimated_remaining_value_chf=round(remaining_value, 0)
        )
    
    def _calculate_rate_from_history(
        self,
        data: List[HistoricalDataPoint]
    ) -> float:
        """Calculate degradation rate from historical data using linear regression"""
        # Sort by date
        sorted_data = sorted(data, key=lambda x: x.date)
        
        # Convert to arrays
        first_date = sorted_data[0].date
        X = np.array([
            (d.date - first_date).days / 365.25 for d in sorted_data
        ]).reshape(-1, 1)
        y = np.array([d.soh_percent for d in sorted_data])
        
        # Fit linear regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Annual rate is negative slope
        annual_rate = -model.coef_[0]
        
        return max(0.5, min(5.0, annual_rate))  # Clamp to reasonable range
    
    def _calculate_empirical_rate(
        self,
        annual_mileage_km: int,
        fast_charge_ratio: float
    ) -> float:
        """Calculate degradation rate from empirical model"""
        # Estimate annual cycles
        # Assume 4 km/kWh efficiency
        annual_kwh = annual_mileage_km / 4
        annual_cycles = annual_kwh / self.original_capacity_kwh
        
        # Base degradation
        calendar_deg = self.calendar_rate * 100  # Convert to %
        cycle_deg = annual_cycles * self.cycle_rate * 100
        
        # Fast charge penalty
        fast_charge_penalty = 1 + (fast_charge_ratio * 0.5)
        cycle_deg *= fast_charge_penalty
        
        return calendar_deg + cycle_deg
    
    def _years_to_threshold(
        self,
        current_soh: float,
        threshold: float,
        annual_rate: float
    ) -> Optional[float]:
        """Calculate years until SoH reaches threshold"""
        if current_soh <= threshold:
            return 0
        
        if annual_rate <= 0:
            return None
        
        years = (current_soh - threshold) / annual_rate
        return years if years > 0 else None
    
    def generate_projection_curve(
        self,
        current_soh: float,
        years_ahead: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Generate SoH projection curve for visualization.
        
        Returns list of (year, soh) tuples.
        """
        annual_rate = self._calculate_empirical_rate(
            self.AVG_ANNUAL_MILEAGE_KM, 0.2
        )
        
        curve = []
        current_year = datetime.now().year
        
        for i in range(years_ahead + 1):
            projected_soh = max(0, current_soh - (annual_rate * i))
            curve.append((current_year + i, round(projected_soh, 1)))
        
        return curve
