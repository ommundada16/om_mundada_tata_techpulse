from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Asset, ThreatScenario
from app.services.ai_tasks import generate_threats_for_asset
from app.services.audit import log_audit
from app.services.serialize import to_dict_list
from app.services import knowledge_base

router = APIRouter(prefix="/threats", tags=["Threats"])


@router.post("/generate/{asset_id}")
def generate_threats(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Retrieval: find the closest matching known threats for this asset
    retrieved = knowledge_base.threat_store.search(asset.description or asset.name, top_k=5)

    # Augmentation + Generation: LLM picks which retrieved threats actually apply
    suggestions = generate_threats_for_asset(asset.name, asset.description, retrieved)

    threat_lookup = {t["metadata"]["threat_id"]: t for t in retrieved}

    created = []
    for suggestion in suggestions:
        threat_id_ref = suggestion.get("threat_id")
        matched = threat_lookup.get(threat_id_ref)
        if not matched:
            continue  # guardrail: skip anything that isn't one of the retrieved, real threats

        threat = ThreatScenario(
            asset_id=asset.id,
            threat_library_ref=threat_id_ref,
            name=matched["metadata"]["name"],
            description=matched["text"],
            reasoning=suggestion.get("reasoning", ""),
            source_citation=f"Threat library entry {threat_id_ref}",
            status="SUGGESTED",
        )
        db.add(threat)
        db.commit()
        db.refresh(threat)
        log_audit(db, "THREAT", threat.id, "CREATE", "system", f"Generated threat: {threat.name}")
        created.append(threat)

    return to_dict_list(created)


@router.get("/by-asset/{asset_id}")
def list_threats_for_asset(asset_id: int, db: Session = Depends(get_db)):
    threats = db.query(ThreatScenario).filter(ThreatScenario.asset_id == asset_id).all()
    return to_dict_list(threats)
