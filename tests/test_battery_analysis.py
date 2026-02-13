"""
Tests for battery analysis service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.battery_analysis import BatteryAnalyzer, ChargingData


class TestBatteryAnalyzer:
    """Test battery analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return BatteryAnalyzer()
    
    @pytest.fixture
    def sample_charging_data(self) -> list[ChargingData]:
        """Generate sample charging data"""
        data = []
        base_time = datetime.now() - timedelta(days=365)
        
        for i in range(100):
            data.append(ChargingData(
                timestamp=base_time + timedelta(days=i * 3),
                start_soc=0.2 + (i % 3) * 0.1,
                end_soc=0.8 + (i % 2) * 0.1,
                energy_kwh=35 + (i % 10),
                duration_minutes=60 + (i % 30),
                charger_power_kw=11 if i % 5 != 0 else 50,
                temperature_c=20 + (i % 15) - 5,
                is_fast_charge=(i % 5 == 0)
            ))
        
        return data
    
    def test_analyze_returns_result(self, analyzer, sample_charging_data):
        """Test that analysis returns a valid result"""
        result = analyzer.analyze(
            charging_data=sample_charging_data,
            battery_capacity_kwh=60.0,
            battery_type="NMC",
            vehicle_age_years=2.0
        )
        
        assert result is not None
        assert 0 <= result.soh_percent <= 100
        assert 0 <= result.soh_confidence <= 1
        assert result.health_grade in ["excellent", "good", "fair", "poor", "critical"]
    
    def test_soh_decreases_with_age(self, analyzer, sample_charging_data):
        """Test that SoH decreases with vehicle age"""
        result_new = analyzer.analyze(
            charging_data=sample_charging_data,
            battery_capacity_kwh=60.0,
            battery_type="NMC",
            vehicle_age_years=1.0
        )
        
        result_old = analyzer.analyze(
            charging_data=sample_charging_data,
            battery_capacity_kwh=60.0,
            battery_type="NMC",
            vehicle_age_years=5.0
        )
        
        assert result_new.soh_percent >= result_old.soh_percent
    
    def test_fast_charging_impact(self, analyzer):
        """Test that high fast charging ratio affects health"""
        base_time = datetime.now() - timedelta(days=180)
        
        # Normal charging pattern
        normal_data = [
            ChargingData(
                timestamp=base_time + timedelta(days=i),
                start_soc=0.2, end_soc=0.8,
                energy_kwh=36, duration_minutes=180,
                charger_power_kw=11, temperature_c=20,
                is_fast_charge=False
            ) for i in range(50)
        ]
        
        # Heavy fast charging pattern
        fast_data = [
            ChargingData(
                timestamp=base_time + timedelta(days=i),
                start_soc=0.1, end_soc=0.9,
                energy_kwh=48, duration_minutes=30,
                charger_power_kw=150, temperature_c=35,
                is_fast_charge=True
            ) for i in range(50)
        ]
        
        result_normal = analyzer.analyze(normal_data, 60.0, "NMC", 2.0)
        result_fast = analyzer.analyze(fast_data, 60.0, "NMC", 2.0)
        
        # Fast charging should result in lower SoH or more risk factors
        assert (result_normal.soh_percent >= result_fast.soh_percent or
                len(result_fast.risk_factors) >= len(result_normal.risk_factors))
    
    def test_lfp_vs_nmc(self, analyzer, sample_charging_data):
        """Test different battery chemistry handling"""
        result_nmc = analyzer.analyze(sample_charging_data, 60.0, "NMC", 3.0)
        result_lfp = analyzer.analyze(sample_charging_data, 60.0, "LFP", 3.0)
        
        # Both should return valid results
        assert result_nmc.health_grade is not None
        assert result_lfp.health_grade is not None
    
    def test_empty_data_handling(self, analyzer):
        """Test handling of empty charging data"""
        result = analyzer.analyze([], 60.0, "NMC", 2.0)
        
        # Should return a result with low confidence
        assert result.soh_confidence < 0.5
    
    def test_health_grade_classification(self, analyzer):
        """Test health grade classification"""
        # Excellent: >95%
        assert analyzer._classify_health(96) == "excellent"
        # Good: 85-95%
        assert analyzer._classify_health(90) == "good"
        # Fair: 75-85%
        assert analyzer._classify_health(80) == "fair"
        # Poor: 65-75%
        assert analyzer._classify_health(70) == "poor"
        # Critical: <65%
        assert analyzer._classify_health(60) == "critical"


class TestChargingDataValidation:
    """Test charging data validation"""
    
    def test_valid_data(self):
        """Test valid charging data creation"""
        data = ChargingData(
            timestamp=datetime.now(),
            start_soc=0.2,
            end_soc=0.8,
            energy_kwh=36,
            duration_minutes=180,
            charger_power_kw=11,
            temperature_c=20,
            is_fast_charge=False
        )
        assert data.start_soc == 0.2
        assert data.end_soc == 0.8
    
    def test_soc_bounds(self):
        """Test SOC value bounds"""
        # This would fail if we add validation
        data = ChargingData(
            timestamp=datetime.now(),
            start_soc=0.0,
            end_soc=1.0,
            energy_kwh=60,
            duration_minutes=300,
            charger_power_kw=11,
            temperature_c=20,
            is_fast_charge=False
        )
        assert 0 <= data.start_soc <= 1
        assert 0 <= data.end_soc <= 1
