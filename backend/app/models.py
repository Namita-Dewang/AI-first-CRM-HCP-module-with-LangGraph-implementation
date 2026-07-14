import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


def gen_id():
    return str(uuid.uuid4())


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    tier = Column(String, nullable=True)
    region = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=gen_id)
    hcp_id = Column(String, ForeignKey("hcps.id"), nullable=True)
    interaction_type = Column(String, default="Meeting")
    date = Column(String, nullable=True)
    time = Column(String, nullable=True)
    attendees = Column(JSON, default=list)
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(JSON, default=list)
    samples_distributed = Column(JSON, default=list)
    sentiment = Column(String, default="Neutral")
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(JSON, default=list)
    compliance_flags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id = Column(String, primary_key=True, default=gen_id)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
    task_description = Column(String, nullable=False)
    due_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
