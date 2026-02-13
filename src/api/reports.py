"""
Reports API
Battery health report generation and retrieval
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..analysis import SoHCalculator, BatteryHealthReport, DegradationPredictor
from ..analysis.soh_calculator import ChargingSession, HealthGrade

router = APIRouter(prefix="/reports")


# ============ Models ============

class AnalysisRequest(BaseModel):
    """Request battery health analysis"""
    vehicle_id: str
    include_prediction: bool = Field(default=True)
    prediction_years: int = Field(default=5, ge=1, le=10)


class HealthReportResponse(BaseModel):
    """Battery health report response"""
    report_id: str
    vehicle_id: str
    analysis_date: datetime
    
    # Core metrics
    soh_percent: float
    soh_confidence: float
    estimated_capacity_kwh: float
    original_capacity_kwh: float
    
    # Classification
    health_grade: str
    health_summary: str
    
    # Usage stats
    total_charging_cycles: int
    total_energy_charged_kwh: float
    avg_charge_level: float
    fast_charge_ratio: float
    
    # Risk & recommendations
    risk_factors: List[str]
    recommendations: List[str]
    
    # Predictions
    predicted_soh_1year: Optional[float] = None
    predicted_soh_3year: Optional[float] = None
    predicted_soh_5year: Optional[float] = None
    years_to_80_percent: Optional[float] = None
    
    # Value impact
    value_impact_chf: Optional[float] = None
    value_impact_percent: Optional[float] = None


class PassportResponse(BaseModel):
    """Battery Value Passport - shareable certificate"""
    passport_id: str
    vehicle_id: str
    vin: Optional[str]
    issued_date: datetime
    valid_until: datetime
    
    # Vehicle info
    make: str
    model: str
    year: int
    mileage_km: Optional[int]
    
    # Battery health
    soh_percent: float
    health_grade: str
    estimated_capacity_kwh: float
    
    # Certification
    certification_hash: str
    qr_code_url: Optional[str] = None
    
    # Predictions
    predicted_soh_1year: Optional[float] = None
    estimated_remaining_years: Optional[float] = None


# ============ In-Memory Storage ============

_reports: dict = {}
_passports: dict = {}

# Import vehicle storage (in real app, use DB)
from .vehicles import _vehicles, _charging_sessions


# ============ Endpoints ============

@router.post("/analyze", response_model=HealthReportResponse, status_code=201)
async def analyze_battery(request: AnalysisRequest):
    """
    Analyze battery health for a vehicle.
    
    Requires charging session data to be uploaded first.
    Returns comprehensive health report with:
    - State of Health (SoH) percentage
    - Health grade classification
    - Risk factors and recommendations
    - Future degradation predictions
    - Market value impact (CHF)
    """
    vehicle_id = request.vehicle_id
    
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = _vehicles[vehicle_id]
    
    # Get charging sessions
    sessions_data = [
        s for s in _charging_sessions.values() 
        if s["vehicle_id"] == vehicle_id
    ]
    
    if not sessions_data:
        raise HTTPException(
            status_code=400, 
            detail="No charging sessions found. Upload charging data first."
        )
    
    # Convert to ChargingSession objects
    sessions = [
        ChargingSession(
            session_id=s["id"],
            timestamp=s["timestamp"],
            start_soc=s["start_soc"],
            end_soc=s["end_soc"],
            energy_kwh=s["energy_kwh"],
            duration_minutes=s["duration_minutes"],
            charger_power_kw=s["charger_power_kw"],
            temperature_c=s.get("temperature_c"),
            is_fast_charge=s.get("is_fast_charge", False)
        )
        for s in sessions_data
    ]
    
    # Calculate vehicle age
    vehicle_age = datetime.now().year - vehicle["year"]
    
    # Run SoH analysis
    calculator = SoHCalculator(original_capacity_kwh=vehicle["battery_capacity_kwh"])
    report = calculator.calculate_soh(
        vehicle_id=vehicle_id,
        charging_sessions=sessions,
        vehicle_age_years=vehicle_age,
        vin=vehicle.get("vin"),
        mileage_km=vehicle.get("mileage_km")
    )
    
    # Run degradation prediction if requested
    predicted_soh_5year = None
    years_to_80 = None
    
    if request.include_prediction:
        predictor = DegradationPredictor(
            battery_type=vehicle.get("battery_type", "NMC"),
            original_capacity_kwh=vehicle["battery_capacity_kwh"]
        )
        prediction = predictor.predict(
            current_soh=report.soh_percent,
            vehicle_age_years=vehicle_age,
            fast_charge_ratio=report.fast_charge_ratio / 100
        )
        predicted_soh_5year = prediction.predicted_soh_5year
        years_to_80 = prediction.years_to_80_percent
    
    # Create report
    report_id = str(uuid4())
    report_data = {
        "report_id": report_id,
        "vehicle_id": vehicle_id,
        "analysis_date": report.analysis_date,
        "soh_percent": report.soh_percent,
        "soh_confidence": report.soh_confidence,
        "estimated_capacity_kwh": report.estimated_capacity_kwh,
        "original_capacity_kwh": report.original_capacity_kwh,
        "health_grade": report.health_grade.value,
        "health_summary": report.health_summary,
        "total_charging_cycles": report.total_charging_cycles,
        "total_energy_charged_kwh": report.total_energy_charged_kwh,
        "avg_charge_level": report.avg_charge_level,
        "fast_charge_ratio": report.fast_charge_ratio,
        "risk_factors": report.risk_factors,
        "recommendations": report.recommendations,
        "predicted_soh_1year": report.predicted_soh_1year,
        "predicted_soh_3year": report.predicted_soh_3year,
        "predicted_soh_5year": predicted_soh_5year,
        "years_to_80_percent": years_to_80,
        "value_impact_chf": report.value_impact_chf,
        "value_impact_percent": report.value_impact_percent
    }
    
    _reports[report_id] = report_data
    
    # Update vehicle last_analysis
    _vehicles[vehicle_id]["last_analysis"] = datetime.now()
    
    return HealthReportResponse(**report_data)


@router.get("/{report_id}", response_model=HealthReportResponse)
async def get_report(report_id: str):
    """Get a specific health report by ID"""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return HealthReportResponse(**_reports[report_id])


@router.get("/vehicle/{vehicle_id}", response_model=List[HealthReportResponse])
async def list_vehicle_reports(
    vehicle_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """List all reports for a vehicle"""
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    reports = [
        r for r in _reports.values() 
        if r["vehicle_id"] == vehicle_id
    ]
    
    # Sort by date descending
    reports.sort(key=lambda x: x["analysis_date"], reverse=True)
    
    return [HealthReportResponse(**r) for r in reports[:limit]]


@router.post("/passport/{vehicle_id}", response_model=PassportResponse, status_code=201)
async def generate_passport(vehicle_id: str):
    """
    Generate a Battery Value Passport for a vehicle.
    
    The passport is a shareable certificate that can be used
    for used car sales to prove battery health.
    
    Requires at least one health analysis to be completed first.
    """
    if vehicle_id not in _vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = _vehicles[vehicle_id]
    
    # Find latest report
    vehicle_reports = [
        r for r in _reports.values() 
        if r["vehicle_id"] == vehicle_id
    ]
    
    if not vehicle_reports:
        raise HTTPException(
            status_code=400, 
            detail="No health analysis found. Run /reports/analyze first."
        )
    
    latest_report = max(vehicle_reports, key=lambda x: x["analysis_date"])
    
    # Generate passport
    import hashlib
    passport_id = str(uuid4())
    
    # Create certification hash
    cert_data = f"{vehicle_id}:{latest_report['soh_percent']}:{datetime.now().isoformat()}"
    cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16]
    
    passport_data = {
        "passport_id": passport_id,
        "vehicle_id": vehicle_id,
        "vin": vehicle.get("vin"),
        "issued_date": datetime.now(),
        "valid_until": datetime(datetime.now().year + 1, 12, 31),
        "make": vehicle["make"],
        "model": vehicle["model"],
        "year": vehicle["year"],
        "mileage_km": vehicle.get("mileage_km"),
        "soh_percent": latest_report["soh_percent"],
        "health_grade": latest_report["health_grade"],
        "estimated_capacity_kwh": latest_report["estimated_capacity_kwh"],
        "certification_hash": cert_hash.upper(),
        "qr_code_url": None,  # Would generate QR code in production
        "predicted_soh_1year": latest_report.get("predicted_soh_1year"),
        "estimated_remaining_years": latest_report.get("years_to_80_percent")
    }
    
    _passports[passport_id] = passport_data
    
    return PassportResponse(**passport_data)


@router.get("/passport/{passport_id}/verify", response_model=PassportResponse)
async def verify_passport(passport_id: str):
    """
    Verify a Battery Value Passport.
    
    Use this endpoint to verify the authenticity of a passport
    when buying a used EV.
    """
    if passport_id not in _passports:
        raise HTTPException(status_code=404, detail="Passport not found or invalid")
    
    passport = _passports[passport_id]
    
    # Check if expired
    if datetime.now() > passport["valid_until"]:
        raise HTTPException(status_code=410, detail="Passport has expired")
    
    return PassportResponse(**passport)
