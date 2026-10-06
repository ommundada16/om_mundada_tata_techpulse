from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Asset, ThreatScenario, RiskAssessment, Mitigation

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/traceability")
def traceability_report(db: Session = Depends(get_db)):
    """Joins Asset -> Threat -> Risk -> Mitigation into one table, the way the case study asks for."""
    rows = []
    assets = db.query(Asset).all()

    for asset in assets:
        threats = db.query(ThreatScenario).filter(ThreatScenario.asset_id == asset.id).all()

        if not threats:
            rows.append({
                "asset": asset.name,
                "threat": None,
                "risk_level": None,
                "mitigation": None,
                "mitigation_status": None,
            })
            continue

        for threat in threats:
            risk = db.query(RiskAssessment).filter(
                RiskAssessment.threat_scenario_id == threat.id
            ).first()
            mitigation = db.query(Mitigation).filter(
                Mitigation.threat_scenario_id == threat.id
            ).first()

            rows.append({
                "asset": asset.name,
                "threat": threat.name,
                "risk_level": risk.risk_level if risk else None,
                "mitigation": mitigation.description if mitigation else None,
                "mitigation_status": mitigation.status if mitigation else None,
            })

    return rows
