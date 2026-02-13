"""
Tests for Degradation Predictor
"""
import pytest
from datetime import datetime, timedelta

from src.analysis.degradation import (
    DegradationPredictor,
    HistoricalDataPoint
)


class TestDegradationPredictor:
    """Test degradation prediction logic"""
    
    def test_nmc_prediction(self):
        """Test NMC battery prediction"""
        predictor = DegradationPredictor(
            battery_type="NMC",
            original_capacity_kwh=75.0
        )
        
        prediction = predictor.predict(
            current_soh=92.0,
            vehicle_age_years=2,
            annual_mileage_km=15000,
            fast_charge_ratio=0.3
        )
        
        assert prediction.current_soh == 92.0
        assert prediction.predicted_soh_1year < 92.0
        assert prediction.predicted_soh_5year < prediction.predicted_soh_1year
        assert prediction.annual_degradation_rate > 0
    
    def test_lfp_prediction(self):
        """Test LFP battery prediction (should degrade slower)"""
        nmc_predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        lfp_predictor = DegradationPredictor(battery_type="LFP", original_capacity_kwh=60.0)
        
        nmc_pred = nmc_predictor.predict(current_soh=95.0, vehicle_age_years=1)
        lfp_pred = lfp_predictor.predict(current_soh=95.0, vehicle_age_years=1)
        
        # LFP should have lower degradation rate
        assert lfp_pred.annual_degradation_rate < nmc_pred.annual_degradation_rate
    
    def test_years_to_threshold(self):
        """Test threshold prediction"""
        predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        
        prediction = predictor.predict(
            current_soh=85.0,
            vehicle_age_years=3
        )
        
        # Should have years to 80% calculated
        assert prediction.years_to_80_percent is not None
        assert prediction.years_to_80_percent > 0
        
        # Should have years to 70% calculated
        assert prediction.years_to_70_percent is not None
        assert prediction.years_to_70_percent > prediction.years_to_80_percent
    
    def test_historical_data_prediction(self):
        """Test prediction with historical data"""
        predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        
        # Create historical data showing 2% annual degradation
        historical = [
            HistoricalDataPoint(
                date=datetime.now() - timedelta(days=730),  # 2 years ago
                soh_percent=100.0
            ),
            HistoricalDataPoint(
                date=datetime.now() - timedelta(days=365),  # 1 year ago
                soh_percent=98.0
            ),
            HistoricalDataPoint(
                date=datetime.now(),
                soh_percent=96.0
            )
        ]
        
        prediction = predictor.predict(
            current_soh=96.0,
            vehicle_age_years=2,
            historical_data=historical
        )
        
        # Should have higher confidence with historical data
        assert prediction.confidence > 0.6
        # Rate should be close to 2%
        assert 1.5 < prediction.annual_degradation_rate < 2.5
    
    def test_fast_charge_impact(self):
        """Test fast charging impact on degradation"""
        predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        
        low_fast = predictor.predict(
            current_soh=95.0,
            vehicle_age_years=1,
            fast_charge_ratio=0.1
        )
        
        high_fast = predictor.predict(
            current_soh=95.0,
            vehicle_age_years=1,
            fast_charge_ratio=0.8
        )
        
        # High fast charging should have higher degradation rate
        assert high_fast.annual_degradation_rate > low_fast.annual_degradation_rate
    
    def test_projection_curve(self):
        """Test projection curve generation"""
        predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        
        curve = predictor.generate_projection_curve(
            current_soh=90.0,
            years_ahead=5
        )
        
        assert len(curve) == 6  # Current year + 5 years
        assert curve[0][1] == 90.0  # First point is current SoH
        
        # Each year should be lower
        for i in range(1, len(curve)):
            assert curve[i][1] < curve[i-1][1]
    
    def test_remaining_value(self):
        """Test remaining value calculation"""
        predictor = DegradationPredictor(
            battery_type="NMC",
            original_capacity_kwh=60.0
        )
        
        prediction = predictor.predict(
            current_soh=80.0,
            vehicle_age_years=5
        )
        
        # 80% of 60kWh = 48kWh, at 150 CHF/kWh = 7200 CHF
        expected_value = 48 * 150
        assert prediction.estimated_remaining_value_chf == expected_value
    
    def test_already_below_threshold(self):
        """Test when SoH is already below threshold"""
        predictor = DegradationPredictor(battery_type="NMC", original_capacity_kwh=60.0)
        
        prediction = predictor.predict(
            current_soh=75.0,  # Already below 80%
            vehicle_age_years=6
        )
        
        assert prediction.years_to_80_percent == 0
        assert prediction.years_to_70_percent is not None
        assert prediction.years_to_70_percent > 0
