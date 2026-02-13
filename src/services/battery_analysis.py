"""
Battery Analysis Service
Core SoH calculation and health assessment
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import math


@dataclass
class ChargingData:
    """Single charging session data"""
    timestamp: datetime
    start_soc: float  # 0-1
    end_soc: float    # 0-1
    energy_kwh: float
    duration_minutes: float
    charger_power_kw: float
    temperature_c: float
    is_fast_charge: bool = False
    
    @property
    def soc_delta(self) -> float:
        return self.end_soc - self.start_soc


@dataclass
class AnalysisResult:
    """Battery health analysis result"""
    soh_percent: float
    soh_confidence: float
    estimated_capacity_kwh: float
    health_grade: str  # excellent, good, fair, poor, critical
    fast_charge_ratio: float
    avg_charge_depth: float
    cycle_count_estimate: int
    degradation_rate_per_year: float
    value_impact_chf: Optional[float] = None
    recommendations: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class BatteryAnalyzer:
    """
    Battery health analyzer using charging data patterns
    """
    
    # Degradation coefficients by battery type
    DEGRADATION_RATES = {
        "NMC": {"base": 0.025, "fast_charge": 0.008, "temp": 0.003},
        "LFP": {"base": 0.015, "fast_charge": 0.004, "temp": 0.002},
    }
    
    # Health grade thresholds
    GRADE_THRESHOLDS = [
        (95, "excellent"),
        (85, "good"),
        (75, "fair"),
        (65, "poor"),
        (0, "critical"),
    ]
    
    def analyze(
        self,
        charging_data: list[ChargingData],
        battery_capacity_kwh: float,
        battery_type: str = "NMC",
        vehicle_age_years: float = 0,
        mileage_km: Optional[int] = None
    ) -> AnalysisResult:
        """
        Analyze battery health from charging data
        
        Args:
            charging_data: List of charging sessions
            battery_capacity_kwh: Original battery capacity
            battery_type: NMC or LFP
            vehicle_age_years: Age of vehicle in years
            mileage_km: Optional odometer reading
        
        Returns:
            AnalysisResult with SoH and recommendations
        """
        if not charging_data:
            return self._empty_result(battery_capacity_kwh, vehicle_age_years, battery_type)
        
        # Calculate metrics from charging data
        fast_charge_ratio = self._calc_fast_charge_ratio(charging_data)
        avg_charge_depth = self._calc_avg_charge_depth(charging_data)
        avg_temp = self._calc_avg_temperature(charging_data)
        cycle_estimate = self._estimate_cycles(charging_data, battery_capacity_kwh)
        
        # Get degradation coefficients
        rates = self.DEGRADATION_RATES.get(battery_type, self.DEGRADATION_RATES["NMC"])
        
        # Calculate degradation factors
        age_degradation = rates["base"] * vehicle_age_years
        fast_charge_degradation = rates["fast_charge"] * fast_charge_ratio * vehicle_age_years
        temp_degradation = rates["temp"] * max(0, (avg_temp - 25) / 10) * vehicle_age_years
        
        # Deep discharge penalty (charging from <20% frequently)
        deep_discharge_penalty = self._calc_deep_discharge_penalty(charging_data)
        
        # Total degradation
        total_degradation = (
            age_degradation + 
            fast_charge_degradation + 
            temp_degradation + 
            deep_discharge_penalty
        )
        
        # Calculate SoH
        soh_percent = max(0, min(100, 100 - (total_degradation * 100)))
        
        # Confidence based on data quality
        confidence = self._calc_confidence(charging_data, vehicle_age_years)
        
        # Estimated remaining capacity
        estimated_capacity = battery_capacity_kwh * (soh_percent / 100)
        
        # Health grade
        health_grade = self._classify_health(soh_percent)
        
        # Degradation rate per year
        degradation_rate = total_degradation / max(vehicle_age_years, 0.5)
        
        # Value impact (rough estimate: CHF 100 per % below 90%)
        value_impact = None
        if soh_percent < 90:
            value_impact = -(90 - soh_percent) * 150  # CHF 150 per percent
        
        # Generate recommendations and risk factors
        recommendations = self._generate_recommendations(
            soh_percent, fast_charge_ratio, avg_charge_depth, avg_temp, battery_type
        )
        risk_factors = self._identify_risks(
            soh_percent, fast_charge_ratio, avg_temp, vehicle_age_years, degradation_rate
        )
        
        return AnalysisResult(
            soh_percent=round(soh_percent, 1),
            soh_confidence=round(confidence, 2),
            estimated_capacity_kwh=round(estimated_capacity, 1),
            health_grade=health_grade,
            fast_charge_ratio=round(fast_charge_ratio * 100, 1),
            avg_charge_depth=round(avg_charge_depth * 100, 1),
            cycle_count_estimate=cycle_estimate,
            degradation_rate_per_year=round(degradation_rate * 100, 2),
            value_impact_chf=value_impact,
            recommendations=recommendations,
            risk_factors=risk_factors
        )
    
    def _empty_result(self, capacity: float, age: float, battery_type: str) -> AnalysisResult:
        """Return result when no charging data available"""
        rates = self.DEGRADATION_RATES.get(battery_type, self.DEGRADATION_RATES["NMC"])
        estimated_soh = 100 - (rates["base"] * age * 100)
        
        return AnalysisResult(
            soh_percent=round(estimated_soh, 1),
            soh_confidence=0.3,  # Low confidence without data
            estimated_capacity_kwh=round(capacity * estimated_soh / 100, 1),
            health_grade=self._classify_health(estimated_soh),
            fast_charge_ratio=0,
            avg_charge_depth=0,
            cycle_count_estimate=0,
            degradation_rate_per_year=rates["base"] * 100,
            recommendations=["Upload charging data for accurate analysis"],
            risk_factors=["Insufficient data for detailed assessment"]
        )
    
    def _calc_fast_charge_ratio(self, data: list[ChargingData]) -> float:
        """Calculate ratio of fast charging sessions"""
        if not data:
            return 0
        fast_count = sum(1 for d in data if d.is_fast_charge or d.charger_power_kw > 50)
        return fast_count / len(data)
    
    def _calc_avg_charge_depth(self, data: list[ChargingData]) -> float:
        """Calculate average charging depth (SOC delta)"""
        if not data:
            return 0
        return sum(d.soc_delta for d in data) / len(data)
    
    def _calc_avg_temperature(self, data: list[ChargingData]) -> float:
        """Calculate average charging temperature"""
        if not data:
            return 20
        return sum(d.temperature_c for d in data) / len(data)
    
    def _estimate_cycles(self, data: list[ChargingData], capacity: float) -> int:
        """Estimate total charge cycles from data"""
        if not data:
            return 0
        total_energy = sum(d.energy_kwh for d in data)
        return int(total_energy / capacity)
    
    def _calc_deep_discharge_penalty(self, data: list[ChargingData]) -> float:
        """Calculate penalty for frequent deep discharges"""
        if not data:
            return 0
        deep_count = sum(1 for d in data if d.start_soc < 0.15)
        ratio = deep_count / len(data)
        return ratio * 0.02  # 2% max penalty
    
    def _calc_confidence(self, data: list[ChargingData], age: float) -> float:
        """Calculate confidence score based on data quality"""
        if not data:
            return 0.3
        
        # More data = higher confidence
        data_score = min(1.0, len(data) / 50)
        
        # Recent data = higher confidence
        if data:
            latest = max(d.timestamp for d in data)
            days_old = (datetime.utcnow() - latest).days
            recency_score = max(0, 1 - (days_old / 180))
        else:
            recency_score = 0
        
        # Data span relative to vehicle age
        if len(data) >= 2:
            span_days = (max(d.timestamp for d in data) - min(d.timestamp for d in data)).days
            span_score = min(1.0, span_days / (age * 365 + 30))
        else:
            span_score = 0.3
        
        return (data_score * 0.4 + recency_score * 0.3 + span_score * 0.3)
    
    def _classify_health(self, soh: float) -> str:
        """Classify health grade from SoH percentage"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if soh >= threshold:
                return grade
        return "critical"
    
    def _generate_recommendations(
        self, soh: float, fast_ratio: float, charge_depth: float, 
        avg_temp: float, battery_type: str
    ) -> list[str]:
        """Generate actionable recommendations"""
        recs = []
        
        if fast_ratio > 0.3:
            recs.append("Reduce fast charging frequency to extend battery life")
        
        if charge_depth > 0.7:
            recs.append("Consider partial charges (20-80%) instead of full cycles")
        
        if avg_temp > 30:
            recs.append("Avoid charging in high temperatures when possible")
        
        if soh < 80:
            recs.append("Consider battery health check at authorized service center")
        
        if battery_type == "LFP" and charge_depth < 0.5:
            recs.append("LFP batteries benefit from occasional full charges for calibration")
        
        if not recs:
            recs.append("Battery health is good - continue current charging habits")
        
        return recs
    
    def _identify_risks(
        self, soh: float, fast_ratio: float, avg_temp: float,
        age: float, degradation_rate: float
    ) -> list[str]:
        """Identify risk factors"""
        risks = []
        
        if soh < 70:
            risks.append("Battery may need replacement within 1-2 years")
        
        if fast_ratio > 0.5:
            risks.append("High fast-charging usage accelerating degradation")
        
        if avg_temp > 35:
            risks.append("Elevated charging temperatures detected")
        
        if degradation_rate > 4:
            risks.append("Above-average degradation rate")
        
        if age > 8 and soh < 80:
            risks.append("Warranty coverage may have expired")
        
        return risks
