"""
Database Models for Malim
SQLAlchemy models with PostgreSQL
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, 
    ForeignKey, Text, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func

import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class HealthGradeEnum(str, enum.Enum):
    """Battery health grade"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class Vehicle(Base):
    """Vehicle model"""
    __tablename__ = "vehicles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vin = Column(String(17), unique=True, nullable=True, index=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    battery_capacity_kwh = Column(Float, nullable=False)
    battery_type = Column(String(20), default="NMC")  # NMC, LFP
    mileage_km = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_analysis = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    charging_sessions = relationship("ChargingSession", back_populates="vehicle", cascade="all, delete-orphan")
    health_reports = relationship("HealthReport", back_populates="vehicle", cascade="all, delete-orphan")
    passports = relationship("BatteryPassport", back_populates="vehicle", cascade="all, delete-orphan")


class ChargingSession(Base):
    """Charging session model"""
    __tablename__ = "charging_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    start_soc = Column(Float, nullable=False)  # 0-1
    end_soc = Column(Float, nullable=False)    # 0-1
    energy_kwh = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    charger_power_kw = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=True)
    is_fast_charge = Column(Boolean, default=False)
    
    # Location (optional)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    charger_id = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="charging_sessions")


class HealthReport(Base):
    """Battery health report model"""
    __tablename__ = "health_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Analysis date
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Core metrics
    soh_percent = Column(Float, nullable=False)
    soh_confidence = Column(Float, nullable=False)
    estimated_capacity_kwh = Column(Float, nullable=False)
    original_capacity_kwh = Column(Float, nullable=False)
    
    # Classification
    health_grade = Column(SQLEnum(HealthGradeEnum), nullable=False)
    health_summary = Column(Text, nullable=True)
    
    # Usage stats
    total_charging_cycles = Column(Integer, default=0)
    total_energy_charged_kwh = Column(Float, default=0)
    avg_charge_level = Column(Float, default=0)
    fast_charge_ratio = Column(Float, default=0)
    
    # Risk & recommendations (stored as JSON)
    risk_factors = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    
    # Predictions
    predicted_soh_1year = Column(Float, nullable=True)
    predicted_soh_3year = Column(Float, nullable=True)
    predicted_soh_5year = Column(Float, nullable=True)
    years_to_80_percent = Column(Float, nullable=True)
    
    # Value impact
    value_impact_chf = Column(Float, nullable=True)
    value_impact_percent = Column(Float, nullable=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="health_reports")


class BatteryPassport(Base):
    """Battery Value Passport model"""
    __tablename__ = "battery_passports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dates
    issued_date = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=False)
    
    # Snapshot of vehicle info at issuance
    vin = Column(String(17), nullable=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    mileage_km = Column(Integer, nullable=True)
    
    # Battery health snapshot
    soh_percent = Column(Float, nullable=False)
    health_grade = Column(SQLEnum(HealthGradeEnum), nullable=False)
    estimated_capacity_kwh = Column(Float, nullable=False)
    
    # Certification
    certification_hash = Column(String(32), unique=True, nullable=False, index=True)
    qr_code_url = Column(String(500), nullable=True)
    
    # Predictions at issuance
    predicted_soh_1year = Column(Float, nullable=True)
    estimated_remaining_years = Column(Float, nullable=True)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="passports")


class KnowledgeDocument(Base):
    """RAG knowledge document model"""
    __tablename__ = "knowledge_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    content = Column(Text, nullable=False)
    doc_type = Column(String(50), default="knowledge")  # faq, technical, market, etc.
    vehicle_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Optional vehicle-specific
    
    # Document metadata (renamed to avoid SQLAlchemy reserved word)
    doc_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
