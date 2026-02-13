"""
Report Repository
Database operations for health reports and passports
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import HealthReport, BatteryPassport, HealthGradeEnum


class HealthReportRepository:
    """Repository for health report database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        vehicle_id: UUID,
        soh_percent: float,
        soh_confidence: float,
        estimated_capacity_kwh: float,
        original_capacity_kwh: float,
        health_grade: HealthGradeEnum,
        health_summary: str,
        total_charging_cycles: int = 0,
        total_energy_charged_kwh: float = 0,
        avg_charge_level: float = 0,
        fast_charge_ratio: float = 0,
        risk_factors: List[str] = None,
        recommendations: List[str] = None,
        predicted_soh_1year: Optional[float] = None,
        predicted_soh_3year: Optional[float] = None,
        predicted_soh_5year: Optional[float] = None,
        years_to_80_percent: Optional[float] = None,
        value_impact_chf: Optional[float] = None,
        value_impact_percent: Optional[float] = None
    ) -> HealthReport:
        """Create a new health report"""
        report = HealthReport(
            vehicle_id=vehicle_id,
            soh_percent=soh_percent,
            soh_confidence=soh_confidence,
            estimated_capacity_kwh=estimated_capacity_kwh,
            original_capacity_kwh=original_capacity_kwh,
            health_grade=health_grade,
            health_summary=health_summary,
            total_charging_cycles=total_charging_cycles,
            total_energy_charged_kwh=total_energy_charged_kwh,
            avg_charge_level=avg_charge_level,
            fast_charge_ratio=fast_charge_ratio,
            risk_factors=risk_factors or [],
            recommendations=recommendations or [],
            predicted_soh_1year=predicted_soh_1year,
            predicted_soh_3year=predicted_soh_3year,
            predicted_soh_5year=predicted_soh_5year,
            years_to_80_percent=years_to_80_percent,
            value_impact_chf=value_impact_chf,
            value_impact_percent=value_impact_percent
        )
        self.session.add(report)
        await self.session.flush()
        return report
    
    async def get_by_id(self, report_id: UUID) -> Optional[HealthReport]:
        """Get report by ID"""
        result = await self.session.execute(
            select(HealthReport).where(HealthReport.id == report_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_vehicle(
        self,
        vehicle_id: UUID,
        limit: int = 10
    ) -> List[HealthReport]:
        """Get reports for a vehicle"""
        result = await self.session.execute(
            select(HealthReport)
            .where(HealthReport.vehicle_id == vehicle_id)
            .order_by(HealthReport.analysis_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_latest_by_vehicle(self, vehicle_id: UUID) -> Optional[HealthReport]:
        """Get latest report for a vehicle"""
        result = await self.session.execute(
            select(HealthReport)
            .where(HealthReport.vehicle_id == vehicle_id)
            .order_by(HealthReport.analysis_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class BatteryPassportRepository:
    """Repository for battery passport database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        vehicle_id: UUID,
        valid_until: datetime,
        vin: Optional[str],
        make: str,
        model: str,
        year: int,
        mileage_km: Optional[int],
        soh_percent: float,
        health_grade: HealthGradeEnum,
        estimated_capacity_kwh: float,
        predicted_soh_1year: Optional[float] = None,
        estimated_remaining_years: Optional[float] = None
    ) -> BatteryPassport:
        """Create a new battery passport"""
        # Generate certification hash
        cert_data = f"{vehicle_id}:{soh_percent}:{datetime.utcnow().isoformat()}"
        cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16].upper()
        
        passport = BatteryPassport(
            vehicle_id=vehicle_id,
            valid_until=valid_until,
            vin=vin,
            make=make,
            model=model,
            year=year,
            mileage_km=mileage_km,
            soh_percent=soh_percent,
            health_grade=health_grade,
            estimated_capacity_kwh=estimated_capacity_kwh,
            certification_hash=cert_hash,
            predicted_soh_1year=predicted_soh_1year,
            estimated_remaining_years=estimated_remaining_years
        )
        self.session.add(passport)
        await self.session.flush()
        return passport
    
    async def get_by_id(self, passport_id: UUID) -> Optional[BatteryPassport]:
        """Get passport by ID"""
        result = await self.session.execute(
            select(BatteryPassport).where(BatteryPassport.id == passport_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, cert_hash: str) -> Optional[BatteryPassport]:
        """Get passport by certification hash"""
        result = await self.session.execute(
            select(BatteryPassport)
            .where(BatteryPassport.certification_hash == cert_hash.upper())
        )
        return result.scalar_one_or_none()
    
    async def get_by_vehicle(self, vehicle_id: UUID) -> List[BatteryPassport]:
        """Get all passports for a vehicle"""
        result = await self.session.execute(
            select(BatteryPassport)
            .where(BatteryPassport.vehicle_id == vehicle_id)
            .order_by(BatteryPassport.issued_date.desc())
        )
        return list(result.scalars().all())
    
    async def is_valid(self, passport_id: UUID) -> bool:
        """Check if passport is still valid"""
        passport = await self.get_by_id(passport_id)
        if not passport:
            return False
        return datetime.utcnow() < passport.valid_until
