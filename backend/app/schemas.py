from typing import Optional
from pydantic import BaseModel


class InteractionCreate(BaseModel):
    hcp_id: Optional[str] = None
    hcp_name: Optional[str] = None
    interaction_type: str = "Meeting"
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: list[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: list[str] = []
    samples_distributed: list[dict] = []
    sentiment: str = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: list[str] = []


class InteractionUpdate(BaseModel):
    updates: dict


class InteractionOut(BaseModel):
    id: str
    hcp_id: Optional[str] = None
    interaction_type: str
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: list[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: list[str] = []
    samples_distributed: list[dict] = []
    sentiment: str
    outcomes: Optional[str] = None
    follow_up_actions: list[str] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    form_state: dict
