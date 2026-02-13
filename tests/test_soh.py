"""
Tests for SoH Calculator
"""
import pytest
from datetime import datetime, timedelta

from src.analysis.soh_calculator import (
    SoHCalculator,
    ChargingSession,
    HealthGrade
)


class TestSoHCalculator:
    """Test SoH calculation logic"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.calculator = SoHCalculator(original_capacity_kwh=60.0)
    
    def _create_sessions(self, count: int, fast_charge_ratio: float = 0.2) -> list:
        """Helper to create test charging sessions"""
        sessions = []
        fast_count = int(count * fast_charge_ratio)
        
        for i in range(count):
            is_fast = i < fast_count
            sessions.append(ChargingSession(
                session_id=f"session_{i}",
                timestamp=datetime.now() - timedelta(days=count - i),
                start_soc=0.2,
                end_soc=0.8,
                energy_kwh=36.0,  # 60% of 60kWh
                duration_minutes=30 if is_fast else 180,
                charger_power_kw=150 if is_fast else 11,
                temperature_c=25,
                is_fast_charge=is_fast
            ))
        
        return sessions
    
    def test_healthy_battery(self):
        """Test analysis of healthy battery"""
        sessions = self._create_sessions(50, fast_charge_ratio=0.1)
        
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=sessions,
            vehicle_age_years=1
        )
        
        assert report.soh_percent > 90
        assert report.health_grade in [HealthGrade.EXCELLENT, HealthGrade.GOOD]
        assert len(report.risk_factors) == 0 or "Schnelllade" not in str(report.risk_factors)
    
    def test_degraded_battery(self):
        """Test analysis with high fast charging"""
        sessions = self._create_sessions(200, fast_charge_ratio=0.7)
        
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=sessions,
            vehicle_age_years=4
        )
        
        assert report.soh_percent < 95
        assert any("Schnelllade" in r for r in report.risk_factors)
    
    def test_high_soc_warning(self):
        """Test warning for high average SOC"""
        sessions = []
        for i in range(50):
            sessions.append(ChargingSession(
                session_id=f"session_{i}",
                timestamp=datetime.now() - timedelta(days=50 - i),
                start_soc=0.7,
                end_soc=1.0,  # Always charging to 100%
                energy_kwh=18.0,
                duration_minutes=60,
                charger_power_kw=11,
                temperature_c=25,
                is_fast_charge=False
            ))
        
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=sessions,
            vehicle_age_years=2
        )
        
        assert any("85%" in r for r in report.risk_factors)
    
    def test_temperature_impact(self):
        """Test temperature impact on degradation"""
        # Hot climate sessions
        hot_sessions = []
        for i in range(50):
            hot_sessions.append(ChargingSession(
                session_id=f"session_{i}",
                timestamp=datetime.now() - timedelta(days=50 - i),
                start_soc=0.2,
                end_soc=0.8,
                energy_kwh=36.0,
                duration_minutes=60,
                charger_power_kw=50,
                temperature_c=40,  # Hot!
                is_fast_charge=True
            ))
        
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=hot_sessions,
            vehicle_age_years=2
        )
        
        assert any("Temperatur" in r for r in report.risk_factors)
    
    def test_health_grades(self):
        """Test health grade classification"""
        assert self.calculator._get_health_grade(98) == HealthGrade.EXCELLENT
        assert self.calculator._get_health_grade(90) == HealthGrade.GOOD
        assert self.calculator._get_health_grade(75) == HealthGrade.FAIR
        assert self.calculator._get_health_grade(60) == HealthGrade.POOR
        assert self.calculator._get_health_grade(40) == HealthGrade.CRITICAL
    
    def test_empty_sessions(self):
        """Test handling of no charging data"""
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=[],
            vehicle_age_years=1
        )
        
        assert report.soh_percent == 0
        assert report.soh_confidence == 0
        assert "Keine Ladedaten" in str(report.risk_factors)
    
    def test_value_impact(self):
        """Test CHF value impact calculation"""
        sessions = self._create_sessions(100, fast_charge_ratio=0.3)
        
        report = self.calculator.calculate_soh(
            vehicle_id="test_vehicle",
            charging_sessions=sessions,
            vehicle_age_years=3
        )
        
        # Value impact should be negative (battery degraded from 100%)
        assert report.value_impact_chf is not None
        assert report.value_impact_chf <= 0
        assert report.value_impact_percent is not None
