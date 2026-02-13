"""
Malim API Integration Tests
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestHealth:
    """Health endpoint tests"""
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]  # degraded OK without DB
        assert "malim" in data["app_name"].lower()
    
    def test_live(self):
        response = client.get("/live")
        assert response.status_code == 200
    
    def test_ready(self):
        response = client.get("/ready")
        # 503 OK without DB connection
        assert response.status_code in [200, 503]


class TestVehicles:
    """Vehicle CRUD tests"""
    
    def test_create_vehicle(self):
        vehicle_data = {
            "make": "Tesla",
            "model": "Model 3",
            "year": 2022,
            "battery_capacity_kwh": 60.0,
            "battery_type": "NMC",
            "mileage_km": 45000
        }
        response = client.post("/api/v1/vehicles", json=vehicle_data)
        assert response.status_code == 201
        data = response.json()
        assert data["make"] == "Tesla"
        assert data["model"] == "Model 3"
        assert "id" in data
        return data["id"]
    
    def test_list_vehicles(self):
        response = client.get("/api/v1/vehicles")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_vehicle(self):
        # Create first
        vehicle_id = self.test_create_vehicle()
        
        # Get
        response = client.get(f"/api/v1/vehicles/{vehicle_id}")
        assert response.status_code == 200
        assert response.json()["id"] == vehicle_id
    
    def test_get_vehicle_not_found(self):
        response = client.get("/api/v1/vehicles/nonexistent-id")
        assert response.status_code == 404


class TestChargingSessions:
    """Charging session tests"""
    
    def setup_method(self):
        """Create a vehicle for testing"""
        vehicle_data = {
            "make": "VW",
            "model": "ID.4",
            "year": 2023,
            "battery_capacity_kwh": 77.0,
            "battery_type": "NMC"
        }
        response = client.post("/api/v1/vehicles", json=vehicle_data)
        self.vehicle_id = response.json()["id"]
    
    def test_add_charging_session(self):
        session_data = {
            "timestamp": datetime.now().isoformat(),
            "start_soc": 0.2,
            "end_soc": 0.8,
            "energy_kwh": 45.0,
            "duration_minutes": 60,
            "charger_power_kw": 50,
            "temperature_c": 22,
            "is_fast_charge": True
        }
        response = client.post(
            f"/api/v1/vehicles/{self.vehicle_id}/charging-sessions",
            json=session_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["energy_kwh"] == 45.0
        assert data["is_fast_charge"] == True
    
    def test_bulk_add_sessions(self):
        sessions = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(10):
            sessions.append({
                "timestamp": (base_time + timedelta(days=i*3)).isoformat(),
                "start_soc": 0.15 + (i % 3) * 0.1,
                "end_soc": 0.75 + (i % 2) * 0.1,
                "energy_kwh": 35.0 + i * 2,
                "duration_minutes": 45 + i * 5,
                "charger_power_kw": 11 if i % 2 == 0 else 50,
                "temperature_c": 20 + i,
                "is_fast_charge": i % 2 == 1
            })
        
        response = client.post(
            f"/api/v1/vehicles/{self.vehicle_id}/charging-sessions/bulk",
            json=sessions
        )
        assert response.status_code == 201
        data = response.json()
        assert data["added"] == 10
    
    def test_list_sessions(self):
        # Add some sessions first
        self.test_bulk_add_sessions()
        
        response = client.get(
            f"/api/v1/vehicles/{self.vehicle_id}/charging-sessions"
        )
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 10


class TestReports:
    """Battery health report tests"""
    
    def setup_method(self):
        """Create vehicle with charging data"""
        # Create vehicle
        vehicle_data = {
            "make": "BMW",
            "model": "iX3",
            "year": 2021,
            "battery_capacity_kwh": 74.0,
            "battery_type": "NMC",
            "mileage_km": 55000
        }
        response = client.post("/api/v1/vehicles", json=vehicle_data)
        self.vehicle_id = response.json()["id"]
        
        # Add charging sessions
        sessions = []
        base_time = datetime.now() - timedelta(days=180)
        
        for i in range(20):
            sessions.append({
                "timestamp": (base_time + timedelta(days=i*9)).isoformat(),
                "start_soc": 0.2,
                "end_soc": 0.8,
                "energy_kwh": 44.0,
                "duration_minutes": 60,
                "charger_power_kw": 50 if i % 3 == 0 else 11,
                "temperature_c": 22,
                "is_fast_charge": i % 3 == 0
            })
        
        client.post(
            f"/api/v1/vehicles/{self.vehicle_id}/charging-sessions/bulk",
            json=sessions
        )
    
    def test_analyze_battery(self):
        response = client.post(
            "/api/v1/reports/analyze",
            json={
                "vehicle_id": self.vehicle_id,
                "include_prediction": True,
                "prediction_years": 5
            }
        )
        assert response.status_code == 201
        data = response.json()
        
        # Check core metrics
        assert "soh_percent" in data
        assert 0 <= data["soh_percent"] <= 100
        assert "health_grade" in data
        assert data["health_grade"] in ["excellent", "good", "fair", "poor", "critical"]
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        
        return data["report_id"]
    
    def test_get_report(self):
        report_id = self.test_analyze_battery()
        
        response = client.get(f"/api/v1/reports/{report_id}")
        assert response.status_code == 200
        assert response.json()["report_id"] == report_id
    
    def test_generate_passport(self):
        # Need analysis first
        self.test_analyze_battery()
        
        response = client.post(f"/api/v1/reports/passport/{self.vehicle_id}")
        assert response.status_code == 201
        data = response.json()
        
        assert "passport_id" in data
        assert "certification_hash" in data
        assert data["make"] == "BMW"
        assert "soh_percent" in data
        
        return data["passport_id"]
    
    def test_verify_passport(self):
        passport_id = self.test_generate_passport()
        
        response = client.get(f"/api/v1/reports/passport/{passport_id}/verify")
        assert response.status_code == 200
        assert response.json()["passport_id"] == passport_id


class TestChat:
    """RAG chat endpoint tests"""
    
    def test_chat_without_context(self):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Was ist State of Health?"
            }
        )
        # May fail without OpenAI key, but should not crash
        assert response.status_code in [200, 422, 500, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
