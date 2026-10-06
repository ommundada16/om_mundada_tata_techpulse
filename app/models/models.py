from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base


class ArchitectureDocument(Base):
    __tablename__ = "architecture_documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    project_name = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="UPLOADED")
    chunk_count = Column(Integer, default=0)

    assets = relationship("Asset", back_populates="document")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("architecture_documents.id"))
    name = Column(String)
    description = Column(Text)
    interface_type = Column(String)
    source_chunk_ref = Column(Text)
    status = Column(String, default="SUGGESTED")
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("ArchitectureDocument", back_populates="assets")
    threats = relationship("ThreatScenario", back_populates="asset")


class ThreatScenario(Base):
    __tablename__ = "threat_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    threat_library_ref = Column(String)
    name = Column(String)
    description = Column(Text)
    reasoning = Column(Text)
    source_citation = Column(Text)
    status = Column(String, default="SUGGESTED")
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset", back_populates="threats")
    risk_assessment = relationship("RiskAssessment", back_populates="threat", uselist=False)
    mitigations = relationship("Mitigation", back_populates="threat")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    threat_scenario_id = Column(Integer, ForeignKey("threat_scenarios.id"), unique=True)
    impact = Column(String)
    feasibility = Column(String)
    risk_level = Column(String)
    rationale = Column(Text)
    assessed_by = Column(String)
    assessed_at = Column(DateTime, default=datetime.utcnow)

    threat = relationship("ThreatScenario", back_populates="risk_assessment")


class Mitigation(Base):
    __tablename__ = "mitigations"

    id = Column(Integer, primary_key=True, index=True)
    threat_scenario_id = Column(Integer, ForeignKey("threat_scenarios.id"))
    mitigation_library_ref = Column(String)
    description = Column(Text)
    status = Column(String, default="DRAFT")
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    threat = relationship("ThreatScenario", back_populates="mitigations")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(Integer)
    action = Column(String)
    performed_by = Column(String)
    performed_at = Column(DateTime, default=datetime.utcnow)
    details = Column(Text)
