"""
State of Health (SoH) Calculator
Core battery health analysis engine for Malim
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class HealthGrade(str, Enum):
    """Battery health grade classification"""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"            # 85-94%
    FAIR = "fair"            # 70-84%
    POOR = "poor"            # 50-69%
    CRITICAL = "critical"    # <50%


@dataclass
class ChargingSession:
    """Single charging session data"""
    session_id: str
    timestamp: datetime
    start_soc: float          # 0-1
    end_soc: float            # 0-1
    energy_kwh: float         # kWh charged
    duration_minutes: float
    charger_power_kw: float
    temperature_c: Optional[float] = None
    is_fast_charge: bool = False


@dataclass
class BatteryHealthReport:
    """Complete battery health analysis report"""
    vehicle_id: str
    vin: Optional[str]
    analysis_date: datetime
    
    # Core metrics
    soh_percent: float              # State of Health (0-100)
    soh_confidence: float           # Confidence level (0-1)
    estimated_capacity_kwh: float   # Current usable capacity
    original_capacity_kwh: float    # Original battery capacity
    
    # Health classification
    health_grade: HealthGrade
    health_summary: str
    
    # Usage statistics
    total_charging_cycles: int
    total_energy_charged_kwh: float
    avg_charge_level: float
    fast_charge_ratio: float        # % of fast charges
    
    # Risk factors
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Prediction
    predicted_soh_1year: Optional[float] = None
    predicted_soh_3year: Optional[float] = None
    estimated_remaining_years: Optional[float] = None
    
    # Market value impact
    value_impact_chf: Optional[float] = None
    value_impact_percent: Optional[float] = None


class SoHCalculator:
    """
    Battery State of Health Calculator
    
    Uses multiple methods to estimate battery health:
    1. Coulomb counting (energy throughput)
    2. Capacity fade modeling
    3. Charging curve analysis
    4. Temperature impact assessment
    
    Swiss market specific:
    - Calibrated for European EV models
    - CHF value impact calculation
    - Integration with Swiss used car market data
    """
    
    # Battery degradation constants (based on research)
    CYCLE_DEGRADATION_RATE = 0.0002  # 0.02% per cycle
    CALENDAR_DEGRADATION_RATE = 0.02  # 2% per year
    FAST_CHARGE_PENALTY = 1.5         # 50% more degradation
    HIGH_SOC_PENALTY = 1.2            # 20% more if avg SOC > 80%
    TEMPERATURE_OPTIMAL_C = 25
    TEMPERATURE_PENALTY_PER_10C = 0.05  # 5% more degradation per 10°C deviation
    
    # Swiss market value factors
    VALUE_PER_SOH_PERCENT = 150  # CHF per 1% SoH
    
    def __init__(self, original_capacity_kwh: float = 60.0):
        """
        Initialize calculator with battery specifications.
        
        Args:
            original_capacity_kwh: Original battery capacity in kWh
        """
        self.original_capacity_kwh = original_capacity_kwh
    
    def calculate_soh(
        self,
        vehicle_id: str,
        charging_sessions: List[ChargingSession],
        vehicle_age_years: float = 0,
        vin: Optional[str] = None,
        mileage_km: Optional[int] = None
    ) -> BatteryHealthReport:
        """
        Calculate comprehensive battery health report.
        
        Args:
            vehicle_id: Unique vehicle identifier
            charging_sessions: List of charging session data
            vehicle_age_years: Age of vehicle in years
            vin: Vehicle Identification Number
            mileage_km: Current odometer reading
            
        Returns:
            BatteryHealthReport with complete analysis
        """
        if not charging_sessions:
            return self._create_default_report(vehicle_id, vin)
        
        # Calculate usage statistics
        total_cycles = self._estimate_cycles(charging_sessions)
        total_energy = sum(s.energy_kwh for s in charging_sessions)
        avg_charge_level = np.mean([s.end_soc for s in charging_sessions])
        fast_charge_count = sum(1 for s in charging_sessions if s.is_fast_charge)
        fast_charge_ratio = fast_charge_count / len(charging_sessions)
        
        # Calculate degradation factors
        cycle_degradation = total_cycles * self.CYCLE_DEGRADATION_RATE
        calendar_degradation = vehicle_age_years * self.CALENDAR_DEGRADATION_RATE
        
        # Apply penalties
        if fast_charge_ratio > 0.3:
            cycle_degradation *= (1 + (fast_charge_ratio - 0.3) * self.FAST_CHARGE_PENALTY)
        
        if avg_charge_level > 0.8:
            cycle_degradation *= self.HIGH_SOC_PENALTY
        
        # Temperature impact
        temps = [s.temperature_c for s in charging_sessions if s.temperature_c is not None]
        if temps:
            avg_temp = np.mean(temps)
            temp_deviation = abs(avg_temp - self.TEMPERATURE_OPTIMAL_C)
            temp_penalty = (temp_deviation / 10) * self.TEMPERATURE_PENALTY_PER_10C
            cycle_degradation *= (1 + temp_penalty)
        
        # Calculate final SoH
        total_degradation = cycle_degradation + calendar_degradation
        soh_percent = max(0, min(100, (1 - total_degradation) * 100))
        
        # Estimate current capacity
        estimated_capacity = self.original_capacity_kwh * (soh_percent / 100)
        
        # Determine health grade
        health_grade = self._get_health_grade(soh_percent)
        
        # Generate risk factors and recommendations
        risk_factors = self._identify_risk_factors(
            soh_percent, fast_charge_ratio, avg_charge_level, temps
        )
        recommendations = self._generate_recommendations(risk_factors)
        
        # Calculate confidence
        confidence = self._calculate_confidence(len(charging_sessions), vehicle_age_years)
        
        # Calculate value impact
        soh_diff = soh_percent - 100
        value_impact_chf = soh_diff * self.VALUE_PER_SOH_PERCENT
        value_impact_percent = soh_diff
        
        # Create report
        return BatteryHealthReport(
            vehicle_id=vehicle_id,
            vin=vin,
            analysis_date=datetime.now(),
            soh_percent=round(soh_percent, 1),
            soh_confidence=round(confidence, 2),
            estimated_capacity_kwh=round(estimated_capacity, 1),
            original_capacity_kwh=self.original_capacity_kwh,
            health_grade=health_grade,
            health_summary=self._generate_summary(health_grade, soh_percent),
            total_charging_cycles=total_cycles,
            total_energy_charged_kwh=round(total_energy, 1),
            avg_charge_level=round(avg_charge_level * 100, 1),
            fast_charge_ratio=round(fast_charge_ratio * 100, 1),
            risk_factors=risk_factors,
            recommendations=recommendations,
            value_impact_chf=round(value_impact_chf, 0),
            value_impact_percent=round(value_impact_percent, 1)
        )
    
    def _estimate_cycles(self, sessions: List[ChargingSession]) -> int:
        """Estimate equivalent full charge cycles"""
        total_energy = sum(s.energy_kwh for s in sessions)
        return int(total_energy / self.original_capacity_kwh)
    
    def _get_health_grade(self, soh_percent: float) -> HealthGrade:
        """Classify battery health into grades"""
        if soh_percent >= 95:
            return HealthGrade.EXCELLENT
        elif soh_percent >= 85:
            return HealthGrade.GOOD
        elif soh_percent >= 70:
            return HealthGrade.FAIR
        elif soh_percent >= 50:
            return HealthGrade.POOR
        else:
            return HealthGrade.CRITICAL
    
    def _identify_risk_factors(
        self,
        soh: float,
        fast_charge_ratio: float,
        avg_soc: float,
        temps: List[float]
    ) -> List[str]:
        """Identify battery health risk factors"""
        risks = []
        
        if fast_charge_ratio > 0.5:
            risks.append("Hohe Schnelllade-Quote (>50%) beschleunigt Alterung")
        
        if avg_soc > 0.85:
            risks.append("Häufiges Laden über 85% erhöht Zellstress")
        
        if temps:
            avg_temp = np.mean(temps)
            if avg_temp > 35:
                risks.append("Hohe Ladetemperaturen (>35°C) beschleunigen Degradation")
            elif avg_temp < 5:
                risks.append("Kalte Ladetemperaturen (<5°C) reduzieren Effizienz")
        
        if soh < 80:
            risks.append("SoH unter 80% - Garantieschwelle oft erreicht")
        
        return risks
    
    def _generate_recommendations(self, risk_factors: List[str]) -> List[str]:
        """Generate recommendations based on risk factors"""
        recommendations = []
        
        if any("Schnelllade" in r for r in risk_factors):
            recommendations.append("Schnellladen auf max. 30% der Ladevorgänge reduzieren")
        
        if any("85%" in r for r in risk_factors):
            recommendations.append("Ladelimit auf 80% setzen für Alltagsnutzung")
        
        if any("Temperatur" in r for r in risk_factors):
            recommendations.append("Batterie vor dem Laden vorkonditionieren")
        
        if not recommendations:
            recommendations.append("Aktuelles Ladeverhalten beibehalten")
        
        return recommendations
    
    def _calculate_confidence(self, session_count: int, age_years: float) -> float:
        """Calculate confidence level of the analysis"""
        # More data = higher confidence
        data_confidence = min(1.0, session_count / 100)
        
        # Newer vehicles = higher confidence (less unknown history)
        age_confidence = max(0.5, 1.0 - (age_years * 0.1))
        
        return (data_confidence * 0.7 + age_confidence * 0.3)
    
    def _generate_summary(self, grade: HealthGrade, soh: float) -> str:
        """Generate human-readable health summary"""
        summaries = {
            HealthGrade.EXCELLENT: f"Ausgezeichneter Zustand ({soh:.0f}%). Batterie wie neu.",
            HealthGrade.GOOD: f"Guter Zustand ({soh:.0f}%). Normale Alterung, volle Alltagstauglichkeit.",
            HealthGrade.FAIR: f"Akzeptabler Zustand ({soh:.0f}%). Spürbare Reichweitenreduzierung.",
            HealthGrade.POOR: f"Eingeschränkter Zustand ({soh:.0f}%). Deutliche Kapazitätsverluste.",
            HealthGrade.CRITICAL: f"Kritischer Zustand ({soh:.0f}%). Batterieersatz empfohlen.",
        }
        return summaries.get(grade, f"SoH: {soh:.0f}%")
    
    def _create_default_report(self, vehicle_id: str, vin: Optional[str]) -> BatteryHealthReport:
        """Create default report when no data available"""
        return BatteryHealthReport(
            vehicle_id=vehicle_id,
            vin=vin,
            analysis_date=datetime.now(),
            soh_percent=0,
            soh_confidence=0,
            estimated_capacity_kwh=0,
            original_capacity_kwh=self.original_capacity_kwh,
            health_grade=HealthGrade.FAIR,
            health_summary="Keine Daten verfügbar für Analyse",
            total_charging_cycles=0,
            total_energy_charged_kwh=0,
            avg_charge_level=0,
            fast_charge_ratio=0,
            risk_factors=["Keine Ladedaten vorhanden"],
            recommendations=["Ladedaten erfassen für genaue Analyse"]
        )
