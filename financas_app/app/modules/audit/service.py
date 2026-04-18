from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.audit.models import AuditLog


def log_action(
    session: Session,
    *,
    user_id: int | None,
    action: str,
    entity: str = "",
    entity_id: int | None = None,
    detail: str = "",
) -> AuditLog:
    row = AuditLog(
        user_id=user_id,
        action=action.strip(),
        entity=entity.strip(),
        entity_id=entity_id,
        detail=detail.strip(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent(session: Session, *, user_id: int, limit: int = 50) -> list[AuditLog]:
    q = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    return list(session.exec(q))

