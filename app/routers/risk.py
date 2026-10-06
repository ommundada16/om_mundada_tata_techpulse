from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import ThreatScenario, RiskAssessment
from app.services.risk_scoring import compute_risk_level
from app.services.audit import log_audit
from app.services.serialize import to_dict
from app.schemas import RiskAssessRequest

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.post("/assess")
def assess_risk(payload: RiskAssessRequest, db: Session = Depends(get_db)):
    threat = db.query(ThreatScenario).filter(ThreatScenario.id == payload.threat_scenario_id).first()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat scenario not found")

    # Plain Python math - NOT an AI call. Risk level must be consistent every time.
    risk_level = compute_risk_level(payload.impact, payload.feasibility)

    existing = db.query(RiskAssessment).filter(
        RiskAssessment.threat_scenario_id == threat.id
    ).first()

    if existing:
        existing.impact = payload.impact
        existing.feasibility = payload.feasibility
        existing.risk_level = risk_level
        existing.assessed_by = payload.assessed_by
        db.commit()
        db.refresh(existing)
        log_audit(db, "RISK", existing.id, "UPDATE", payload.assessed_by, f"Risk re-assessed: {risk_level}")
        return to_dict(existing)

    assessment = RiskAssessment(
        threat_scenario_id=threat.id,
        impact=payload.impact,
        feasibility=payload.feasibility,
        risk_level=risk_level,
        rationale=f"Impact={payload.impact}, Feasibility={payload.feasibility} -> {risk_level}",
        assessed_by=payload.assessed_by,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    log_audit(db, "RISK", assessment.id, "CREATE", payload.assessed_by, f"Risk assessed: {risk_level}")
    return to_dict(assessment)
