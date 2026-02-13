"""
Vehicles API
Vehicle management and battery data endpoints
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/vehicles")


# ============ Models ============

class VehicleCreate(BaseModel):
    """Create vehicle request"""
    vin: Optional[str] = None
    make: str = Field(..., example="Tesla")
    model: str = Field(..., example="Model 3")
    year: int = Field(..., ge=2010, le=2030, example=2022)
    battery_capacity_kwh: float = Field(..., gt=0, example=60.0)
    battery_type: str = Field(default="NMC", example="NMC")  # NMC, LFP
    mileage_km: Optional[int] = Field(default=None, ge=0, example=45000)


class VehicleResponse(BaseModel):
    """Vehicle response"""
    id: str
    vin: Optional[str]
    make: str
    model: str
    year: int
    battery_capacity_kwh: float
    battery_type: str
    mileage_km: Optional[int]
    created_at: datetime
    last_analysis: Optional[datetime] = None


class ChargingSessionCreate(BaseModel):
    """Create charging session request"""
    timestamp: datetime
    start_soc: float = Field(..., ge=0, le=1, example=0.2)
    end_soc: float = Field(..., ge=0, le=1, example=0.8)
    energy_kwh: float = Field(..., gt=0, example=35.0)
    duration_minutes: float = Field(..., gt=0, example=45)
    charger_power_kw: float = Field(..., gt=0, example=50)
    temperature_c: Optional[float] = Field(default=None, example=22)
    is_fast_charge: bool = Field(default=False)


class ChargingSessionResponse(BaseModel):
    """Charging session response"""
    id: str
    vehicle_id: str
    timestamp: datetime
    start_soc: float
    end_soc: float
    energy_kwh: float
    duration_minutes: float
    charger_power_kw: float
    temperature_c: Optional[float]
    is_fast_charge: bool


# ============ In-Memory Storage (replace with DB) ============

_vehicles: dict = {}
_charging_sessions: dict = {}


# ============ Endpoints ============

@router.post("", response_model=VehicleResponse, status_code=201)
async def create_vehicle(vehicle: VehicleCreate):
    """
    Register a new vehicle for battery health tracking.
    
    Required fields:
    - make: Vehicle manufacturer
    - model: Vehicle model name
    - year: Manufacturing year
    - battery_capacity_kwh: Original battery capacity
    """
    vehicle_id = str(uuid4())
    
    vehicle_data = {
        "id": vehicle_id,
        "vin": vehicle.vin,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "battery_capacity_kwh": vehicle.battery_capacity_kwh,
        "battery_type": vehicle.battery_type,
        "mileage_km": vehicle.mileage_km,
        "created_at": datetime.now(),
        "last_analysis": None
    }
    
    _vehicles[vehicle_id] = vehicle_data
    return VehicleResponse(**vehicle_data)


@router.get("", response_model=List[VehicleResponse])
async def list_vehicles(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List all registered vehicles"""
    vehicles = list(_vehicles.values())
    return [VehicleResponse(**v) for v in vehicles[offset:offset + limit]]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: str):
    """Get vehicle details by ID"""
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return VehicleResponse(**_vehicles[vehicle_id])


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: str):
    """Delete a vehicle and all associated data"""
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    del _vehicles[vehicle_id]
    
    # Delete associated charging sessions
    sessions_to_delete = [
        sid for sid, s in _charging_sessions.items() 
        if s["vehicle_id"] == vehicle_id
    ]
    for sid in sessions_to_delete:
        del _charging_sessions[sid]


@router.post("/{vehicle_id}/charging-sessions", response_model=ChargingSessionResponse, status_code=201)
async def add_charging_session(vehicle_id: str, session: ChargingSessionCreate):
    """
    Add a charging session for a vehicle.
    
    This data is used to calculate battery health (SoH).
    More sessions = more accurate analysis.
    """
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    session_id = str(uuid4())
    
    session_data = {
        "id": session_id,
        "vehicle_id": vehicle_id,
        "timestamp": session.timestamp,
        "start_soc": session.start_soc,
        "end_soc": session.end_soc,
        "energy_kwh": session.energy_kwh,
        "duration_minutes": session.duration_minutes,
        "charger_power_kw": session.charger_power_kw,
        "temperature_c": session.temperature_c,
        "is_fast_charge": session.is_fast_charge
    }
    
    _charging_sessions[session_id] = session_data
    return ChargingSessionResponse(**session_data)


@router.get("/{vehicle_id}/charging-sessions", response_model=List[ChargingSessionResponse])
async def list_charging_sessions(
    vehicle_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List charging sessions for a vehicle"""
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    sessions = [
        s for s in _charging_sessions.values() 
        if s["vehicle_id"] == vehicle_id
    ]
    
    # Sort by timestamp descending
    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return [ChargingSessionResponse(**s) for s in sessions[offset:offset + limit]]


@router.post("/{vehicle_id}/charging-sessions/bulk", response_model=dict, status_code=201)
async def bulk_add_charging_sessions(vehicle_id: str, sessions: List[ChargingSessionCreate]):
    """
    Bulk add charging sessions for a vehicle.
    
    Use this endpoint to import historical charging data.
    Maximum 500 sessions per request.
    """
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if len(sessions) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 sessions per request")
    
    added_count = 0
    for session in sessions:
        session_id = str(uuid4())
        session_data = {
            "id": session_id,
            "vehicle_id": vehicle_id,
            "timestamp": session.timestamp,
            "start_soc": session.start_soc,
            "end_soc": session.end_soc,
            "energy_kwh": session.energy_kwh,
            "duration_minutes": session.duration_minutes,
            "charger_power_kw": session.charger_power_kw,
            "temperature_c": session.temperature_c,
            "is_fast_charge": session.is_fast_charge
        }
        _charging_sessions[session_id] = session_data
        added_count += 1
    
    return {"added": added_count, "total": len(_charging_sessions)}
