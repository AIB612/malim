"""
Vehicle Repository
Database operations for vehicles
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import Vehicle, ChargingSession


class VehicleRepository:
    """Repository for vehicle database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        make: str,
        model: str,
        year: int,
        battery_capacity_kwh: float,
        battery_type: str = "NMC",
        vin: Optional[str] = None,
        mileage_km: Optional[int] = None
    ) -> Vehicle:
        """Create a new vehicle"""
        vehicle = Vehicle(
            make=make,
            model=model,
            year=year,
            battery_capacity_kwh=battery_capacity_kwh,
            battery_type=battery_type,
            vin=vin,
            mileage_km=mileage_km
        )
        self.session.add(vehicle)
        await self.session.flush()
        return vehicle
    
    async def get_by_id(self, vehicle_id: UUID) -> Optional[Vehicle]:
        """Get vehicle by ID"""
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_vin(self, vin: str) -> Optional[Vehicle]:
        """Get vehicle by VIN"""
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.vin == vin)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, limit: int = 50, offset: int = 0) -> List[Vehicle]:
        """List all vehicles with pagination"""
        result = await self.session.execute(
            select(Vehicle)
            .order_by(Vehicle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def update(self, vehicle_id: UUID, **kwargs) -> Optional[Vehicle]:
        """Update vehicle fields"""
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return None
        
        for key, value in kwargs.items():
            if hasattr(vehicle, key):
                setattr(vehicle, key, value)
        
        vehicle.updated_at = datetime.utcnow()
        await self.session.flush()
        return vehicle
    
    async def delete(self, vehicle_id: UUID) -> bool:
        """Delete vehicle and all related data"""
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return False
        
        await self.session.delete(vehicle)
        return True
    
    async def update_last_analysis(self, vehicle_id: UUID) -> None:
        """Update last analysis timestamp"""
        await self.update(vehicle_id, last_analysis=datetime.utcnow())


class ChargingSessionRepository:
    """Repository for charging session database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        vehicle_id: UUID,
        timestamp: datetime,
        start_soc: float,
        end_soc: float,
        energy_kwh: float,
        duration_minutes: float,
        charger_power_kw: float,
        temperature_c: Optional[float] = None,
        is_fast_charge: bool = False
    ) -> ChargingSession:
        """Create a new charging session"""
        session = ChargingSession(
            vehicle_id=vehicle_id,
            timestamp=timestamp,
            start_soc=start_soc,
            end_soc=end_soc,
            energy_kwh=energy_kwh,
            duration_minutes=duration_minutes,
            charger_power_kw=charger_power_kw,
            temperature_c=temperature_c,
            is_fast_charge=is_fast_charge
        )
        self.session.add(session)
        await self.session.flush()
        return session
    
    async def bulk_create(
        self,
        vehicle_id: UUID,
        sessions_data: List[dict]
    ) -> int:
        """Bulk create charging sessions"""
        sessions = [
            ChargingSession(vehicle_id=vehicle_id, **data)
            for data in sessions_data
        ]
        self.session.add_all(sessions)
        await self.session.flush()
        return len(sessions)
    
    async def get_by_vehicle(
        self,
        vehicle_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChargingSession]:
        """Get charging sessions for a vehicle"""
        result = await self.session.execute(
            select(ChargingSession)
            .where(ChargingSession.vehicle_id == vehicle_id)
            .order_by(ChargingSession.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_all_by_vehicle(self, vehicle_id: UUID) -> List[ChargingSession]:
        """Get all charging sessions for a vehicle (for analysis)"""
        result = await self.session.execute(
            select(ChargingSession)
            .where(ChargingSession.vehicle_id == vehicle_id)
            .order_by(ChargingSession.timestamp.asc())
        )
        return list(result.scalars().all())
    
    async def count_by_vehicle(self, vehicle_id: UUID) -> int:
        """Count charging sessions for a vehicle"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(ChargingSession.id))
            .where(ChargingSession.vehicle_id == vehicle_id)
        )
        return result.scalar() or 0
