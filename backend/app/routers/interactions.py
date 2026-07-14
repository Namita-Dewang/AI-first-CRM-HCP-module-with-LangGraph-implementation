from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HCP, Interaction
from ..schemas import InteractionCreate, InteractionOut, InteractionUpdate

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    """Direct form-submission path (no chat/LLM involved) — used when the
    rep fills out the structured form instead of the chat panel."""
    hcp_id = payload.hcp_id
    if not hcp_id and payload.hcp_name:
        hcp = db.query(HCP).filter(HCP.name.ilike(payload.hcp_name)).first()
        if not hcp:
            hcp = HCP(name=payload.hcp_name)
            db.add(hcp)
            db.commit()
            db.refresh(hcp)
        hcp_id = hcp.id

    row = Interaction(
        hcp_id=hcp_id,
        interaction_type=payload.interaction_type,
        date=payload.date,
        time=payload.time,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=payload.materials_shared,
        samples_distributed=payload.samples_distributed,
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    row = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return row


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: str, payload: InteractionUpdate, db: Session = Depends(get_db)):
    row = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    for key, value in payload.updates.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[InteractionOut])
def list_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()
