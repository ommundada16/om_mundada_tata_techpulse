from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Asset, ArchitectureDocument
from app.services.ai_tasks import extract_assets_from_text
from app.services.audit import log_audit
from app.services.serialize import to_dict_list
from app.services import knowledge_base

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("/extract")
def extract_assets(db: Session = Depends(get_db)):
    # make sure there's one document row to attach assets to (we auto-ingest at startup)
    document = db.query(ArchitectureDocument).first()
    if not document:
        document = ArchitectureDocument(
            file_name="architecture.txt",
            project_name="Connected Vehicle Telematics",
            status="INGESTED",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

    extracted = extract_assets_from_text(knowledge_base.architecture_full_text)

    created_assets = []
    for item in extracted:
        asset = Asset(
            document_id=document.id,
            name=item.get("name", "Unknown Asset"),
            description=item.get("description", ""),
            interface_type=item.get("interface_type", ""),
            source_chunk_ref="architecture.txt",
            status="SUGGESTED",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        log_audit(db, "ASSET", asset.id, "CREATE", "system", f"Extracted asset: {asset.name}")
        created_assets.append(asset)

    return to_dict_list(created_assets)


@router.get("/")
def list_assets(db: Session = Depends(get_db)):
    return to_dict_list(db.query(Asset).all())
