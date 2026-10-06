from app.models.models import AuditLog


def log_audit(db, entity_type: str, entity_id: int, action: str, performed_by: str, details: str = ""):
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        details=details,
    )
    db.add(entry)
    db.commit()
