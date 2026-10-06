from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.database import get_db
from app.models.models import ThreatScenario, Mitigation
from app.services.ai_tasks import suggest_mitigation_for_threat
from app.services.audit import log_audit
from app.services.serialize import to_dict
from app.schemas import ApproveMitigationRequest
from app.services import knowledge_base

router = APIRouter(prefix="/mitigations", tags=["Mitigations"])


@router.post("/suggest/{threat_id}")
def suggest_mitigation(threat_id: int, db: Session = Depends(get_db)):
    threat = db.query(ThreatScenario).filter(ThreatScenario.id == threat_id).first()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    retrieved = knowledge_base.mitigation_store.search(threat.description, top_k=3)
    result = suggest_mitigation_for_threat(
        threat.name, threat.description, retrieved, threat.threat_library_ref or ""
    )

    if not result:
        # Guardrail: if the AI didn't return something usable, don't save garbage - tell the user instead.
        raise HTTPException(status_code=422, detail="AI could not generate a confident mitigation suggestion")

    mitigation = Mitigation(
        threat_scenario_id=threat.id,
        mitigation_library_ref=result.get("mitigation_id", ""),
        description=result.get("description", ""),
        status="DRAFT",
    )
    db.add(mitigation)
    db.commit()
    db.refresh(mitigation)
    log_audit(db, "MITIGATION", mitigation.id, "CREATE", "system", "Draft mitigation suggested")
    return to_dict(mitigation)


@router.post("/{mitigation_id}/approve")
def approve_mitigation(mitigation_id: int, payload: ApproveMitigationRequest, db: Session = Depends(get_db)):
    mitigation = db.query(Mitigation).filter(Mitigation.id == mitigation_id).first()
    if not mitigation:
        raise HTTPException(status_code=404, detail="Mitigation not found")

    # Human-in-the-loop: nothing becomes APPROVED until a person clicks this.
    mitigation.status = "APPROVED"
    mitigation.approved_by = payload.approved_by
    mitigation.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(mitigation)
    log_audit(db, "MITIGATION", mitigation.id, "APPROVE", payload.approved_by, "Mitigation approved")
    return to_dict(mitigation)
