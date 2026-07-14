"""
LangGraph agent for the HCP interaction assistant.

Graph shape:  START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

The agent node calls the Groq LLM (bound to the 5 tools below). If the LLM
requests a tool call, the tools node executes it and control returns to the
agent node. This loops until the LLM responds without requesting a tool,
at which point the graph ends and the accumulated state (which mirrors the
frontend's Redux interaction slice) is returned to FastAPI.
"""
import json
import re
import uuid
import os
from datetime import datetime
from typing import Annotated, Optional, TypedDict
from groq import BadRequestError, RateLimitError
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .database import SessionLocal
from .models import HCP, FollowUpTask, Interaction

SAMPLE_ANNUAL_LIMIT = 10  # illustrative PDMA-style cap per HCP per product per year
FUNCTION_LEAK_RE = re.compile(r"<function=(\w+)>(\{.*?\})</function>", re.DOTALL)
SUGGESTION_RE = re.compile(r"^SUGGESTION:\s*(.+)$", re.MULTILINE)
APPROVED_MATERIALS = [
    "OncoBoost Phase III PDF",
    "OncoBoost Efficacy One-Pager",
    "Product X Safety Summary",
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class InteractionState(TypedDict):
    messages: Annotated[list, add_messages]
    interaction_id: Optional[str]
    hcp_id: Optional[str]
    hcp_name: Optional[str]
    interaction_type: Optional[str]
    date: Optional[str]
    time: Optional[str]
    attendees: list[str]
    topics_discussed: Optional[str]
    materials_shared: list[str]
    samples_distributed: list[dict]
    sentiment: Optional[str]
    outcomes: Optional[str]
    follow_up_actions: list[str]
    compliance_flags: list[str]
    ai_suggested_follow_ups: list[str]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool
def get_hcp_context(hcp_name_query: str) -> dict:
    """Look up an HCP by name or partial name. Returns their profile and
    recent interaction history. Call this FIRST whenever an HCP is
    mentioned, before logging or editing anything, so the interaction can
    be tied to the correct HCP record."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name_query}%")).first()
        if not hcp:
            return {"found": False, "query": hcp_name_query}
        recent = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.created_at.desc())
            .limit(3)
            .all()
        )
        return {
            "found": True,
            "hcp_id": hcp.id,
            "name": hcp.name,
            "specialty": hcp.specialty,
            "tier": hcp.tier,
            "recent_interactions": [
                {"date": r.date, "sentiment": r.sentiment, "outcomes": r.outcomes} for r in recent
            ],
        }
    finally:
        db.close()


@tool
def recommend_compliant_content(hcp_id: str, topics: list[str] = [], proposed_samples: Optional[list[dict]] = None) -> dict:
    """Given topics discussed and any samples the rep wants to distribute,
    returns MLR-approved materials to suggest and checks sample compliance
    against the annual per-HCP limit. Call this BEFORE log_interaction
    whenever samples or materials are mentioned."""
    db = SessionLocal()
    try:
        year_start = datetime(datetime.utcnow().year, 1, 1)
        prior = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp_id, Interaction.created_at >= year_start)
            .all()
        )
        distributed_so_far = sum(
            s.get("quantity", 0) for i in prior for s in (i.samples_distributed or [])
        )
        proposed_qty = sum(s.get("quantity", 0) for s in (proposed_samples or []))
        eligible = (distributed_so_far + proposed_qty) <= SAMPLE_ANNUAL_LIMIT

        matched_materials = [m for m in APPROVED_MATERIALS if any(t.lower() in m.lower() for t in topics)] or APPROVED_MATERIALS[:1]

        return {
            "approved_materials": matched_materials,
            "sample_check": {
                "eligible": eligible,
                "distributed_this_year": distributed_so_far,
                "annual_limit": SAMPLE_ANNUAL_LIMIT,
                "remaining": max(0, SAMPLE_ANNUAL_LIMIT - distributed_so_far),
            },
        }
    finally:
        db.close()


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}(\s?[APap][Mm])?$")


@tool
def log_interaction(interaction: dict) -> dict:
    """Persist a NEW HCP interaction record. `interaction` should include
    EITHER hcp_id (if get_hcp_context found an existing HCP) OR hcp_name
    (if get_hcp_context returned found=False) — never ask the rep for a
    numeric ID. Only include date/time if the rep stated an explicit
    date (YYYY-MM-DD) or time (HH:MM) — NEVER pass words like "today",
    "now", or "just now" as the value; omit the field entirely instead
    and the system will stamp the real current date/time automatically.
    Also include interaction_type, attendees, topics_discussed,
    materials_shared, samples_distributed, sentiment (one of Positive,
    Neutral, Negative), outcomes, and follow_up_actions."""
    db = SessionLocal()
    try:
        hcp_id = interaction.get("hcp_id")
        if not hcp_id and interaction.get("hcp_name"):
            hcp = db.query(HCP).filter(HCP.name.ilike(interaction["hcp_name"])).first()
            if not hcp:
                hcp = HCP(name=interaction["hcp_name"])
                db.add(hcp)
                db.commit()
                db.refresh(hcp)
            hcp_id = hcp.id

        now = datetime.now()
        raw_date = interaction.get("date")
        raw_time = interaction.get("time")
        date = raw_date if raw_date and DATE_RE.match(raw_date) else now.strftime("%Y-%m-%d")
        time = raw_time if raw_time and TIME_RE.match(raw_time) else now.strftime("%H:%M")

        row = Interaction(
            hcp_id=hcp_id,
            interaction_type=interaction.get("interaction_type", "Meeting"),
            date=date,
            time=time,
            attendees=interaction.get("attendees", []),
            topics_discussed=interaction.get("topics_discussed"),
            materials_shared=interaction.get("materials_shared", []),
            samples_distributed=interaction.get("samples_distributed", []),
            sentiment=interaction.get("sentiment", "Neutral"),
            outcomes=interaction.get("outcomes"),
            follow_up_actions=interaction.get("follow_up_actions", []),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"interaction_id": row.id, "hcp_id": hcp_id, "status": "logged", "date": date, "time": time}
    finally:
        db.close()


@tool
def edit_interaction(interaction_id: str, updates: dict) -> dict:
    """Update specific fields on an existing interaction. Only include the
    fields that changed, e.g. {"sentiment": "Neutral"}."""
    db = SessionLocal()
    try:
        row = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not row:
            return {"status": "not_found", "interaction_id": interaction_id}
        for key, value in updates.items():
            if hasattr(row, key):
                setattr(row, key, value)
        db.commit()
        return {"interaction_id": interaction_id, "status": "updated", "updated_fields": updates}
    finally:
        db.close()


@tool
def schedule_followup_task(interaction_id: str, task_description: str, due_date: str) -> dict:
    """Create a follow-up task/reminder tied to an interaction, e.g. for
    scheduling a next meeting or sending a document."""
    db = SessionLocal()
    try:
        task = FollowUpTask(
            interaction_id=interaction_id, task_description=task_description, due_date=due_date
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {"task_id": task.id, "due_date": due_date}
    finally:
        db.close()


TOOLS = [
    get_hcp_context,
    recommend_compliant_content,
    log_interaction,
    edit_interaction,
    schedule_followup_task,
]

TOOL_MAP = {t.name: t for t in TOOLS}

_PLACEHOLDER_VALUES = {"", "none", "null", "n/a", "na"}

def _as_list(value, fallback):
    if value is None:
        return fallback
    items = value if isinstance(value, list) else [value]
    cleaned = [str(i).strip() for i in items if i is not None and str(i).strip().lower() not in _PLACEHOLDER_VALUES]
    return cleaned if cleaned else fallback


EDIT_FIELD_ALIASES = {
    "observed": "sentiment",
    "hcp_sentiment": "sentiment",
    "type": "interaction_type",
}


def tools_node(state: InteractionState):
    last_message = state["messages"][-1]
    tool_messages = []
    patch = {}

    for call in last_message.tool_calls:
        try:
            result = TOOL_MAP[call["name"]].invoke(call["args"])
        except Exception as e:
            result = {"status": "error", "message": f"Tool call failed: {e}"}
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"]))

        if call["name"] == "get_hcp_context" and result.get("found"):
            patch["hcp_id"] = result.get("hcp_id")
            patch["hcp_name"] = result.get("name")

        elif call["name"] == "log_interaction":
            # A brand-new DB row was just created — reflect ONLY this
            # interaction, don't inherit leftover fields from whatever
            # was logged before it in this session.
            interaction = call["args"].get("interaction", {})
            patch.update({
                "interaction_id": result.get("interaction_id"),
                "hcp_id": result.get("hcp_id") or interaction.get("hcp_id"),
                "hcp_name": interaction.get("hcp_name"),
                "interaction_type": interaction.get("interaction_type", "Meeting"),
                "date": result.get("date"),
                "time": result.get("time"),
                "attendees": _as_list(interaction.get("attendees"), []),
                "topics_discussed": interaction.get("topics_discussed"),
                "materials_shared": _as_list(interaction.get("materials_shared"), []),
                "samples_distributed": _as_list(interaction.get("samples_distributed"), []),
                "sentiment": interaction.get("sentiment", "Neutral"),
                "outcomes": interaction.get("outcomes"),
                "follow_up_actions": _as_list(interaction.get("follow_up_actions"), []),
                "compliance_flags": [],
            })

        elif call["name"] == "edit_interaction":
            raw_updates = call["args"].get("updates", {})
            normalized = {}
            for k, v in raw_updates.items():
                key = EDIT_FIELD_ALIASES.get(k, k)
                if key in ("attendees", "materials_shared", "samples_distributed", "follow_up_actions"):
                    v = _as_list(v, [])
                normalized[key] = v
            patch.update(normalized)

        elif call["name"] == "recommend_compliant_content":
            check = result.get("sample_check", {})
            if check and not check.get("eligible", True):
                flags = state.get("compliance_flags", []) + [
                    f"Sample limit exceeded: {check.get('distributed_this_year')}/{check.get('annual_limit')}"
                ]
                patch["compliance_flags"] = flags

        elif call["name"] == "schedule_followup_task":
            desc = call["args"].get("task_description")
            if desc:
                patch["follow_up_actions"] = state.get("follow_up_actions", []) + [desc]

    patch["messages"] = tool_messages
    return patch

SYSTEM_PROMPT = SYSTEM_PROMPT = SYSTEM_PROMPT = """You are a field-rep assistant for a pharmaceutical CRM.
You help log and edit HCP interactions from natural language, and you keep
the rep compliant. Always call get_hcp_context first when an HCP is named.
If get_hcp_context returns found=False, do NOT ask the rep for an ID —
there is no such field. Just proceed and call log_interaction with
hcp_name instead of hcp_id; a new HCP record will be created
automatically. Always call recommend_compliant_content before logging
samples or materials, and never log a sample quantity that check flags as
ineligible without warning the rep.

Only these exact field names exist: hcp_name, interaction_type, date,
time, attendees, topics_discussed, materials_shared,
samples_distributed, sentiment, outcomes, follow_up_actions. Never
invent other field names.

NEVER ask the rep for date or time — always omit them and the actual
current timestamp is used automatically. NEVER ask the rep for
interaction_type — if it isn't clearly stated, default to "Meeting"
and log_interaction will handle it, do not ask about it. Extract
whatever topics_discussed, outcomes, sentiment, materials, or samples
you can infer from what the rep actually said, even partial
information, and call log_interaction immediately with what you have.

The ONLY acceptable reason to ask a clarifying question before logging
is if you cannot determine who the HCP is at all (no name given). For
everything else — interaction type, date, time, sentiment, exact
wording of topics — make a reasonable inference from the message and
log it rather than asking. The rep can always correct details
afterward with edit_interaction.

Once an interaction has already been logged in this conversation, treat
any new information the rep provides as a correction and immediately
call edit_interaction with interaction_id and only the changed fields
— do not ask further questions about it.

After every successful log_interaction or edit_interaction call, think
of 2-3 concrete, specific next-step suggestions for the rep based on
what was just discussed. List them at the very end of your reply, each
on its own line starting with "SUGGESTION: ". Do not use this format
at any other time.

Keep replies short and rep-friendly."""


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
_compiled_graph = None


def get_agent_graph():
    """Lazily builds and caches the compiled LangGraph app. Raises a clear
    error if GROQ_API_KEY isn't set, rather than failing at import time."""
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is not set. Create a key at console.groq.com and "
            "set it as an environment variable before starting the server."
        )

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: InteractionState):
        messages = state["messages"]

        turns_since_user = 0
        for m in reversed(messages):
            if isinstance(m, HumanMessage) or (isinstance(m, tuple) and m[0] == "user"):
                break
            if isinstance(m, AIMessage):
                turns_since_user += 1

        recent_messages = messages[-10:]

        try:
            if turns_since_user >= 5:
                response = llm.invoke(
                    [("system", SYSTEM_PROMPT + "\n\nRespond now with a short final answer in plain text. Do not call any more tools.")]
                    + recent_messages
                )
            else:
                response = llm_with_tools.invoke([("system", SYSTEM_PROMPT)] + recent_messages)
                
        except RateLimitError as e:
            response = AIMessage(
                content=(
                    "I've hit Groq's rate limit for right now and can't process this message. "
                    "Please wait a few minutes and try again."
                )
            )
        except BadRequestError:
            response = llm.invoke(
                [("system", SYSTEM_PROMPT + "\n\nRespond with a short plain-text answer only. Do not attempt to call any tools.")]
                + recent_messages
            )

        content = response.content or ""
        match = FUNCTION_LEAK_RE.search(content)

        if match:
            if getattr(response, "tool_calls", None):
                # A real tool call already fired correctly — just strip the
                # redundant leaked text so the rep doesn't see raw syntax.
                cleaned = FUNCTION_LEAK_RE.sub("", content).strip()
                response = AIMessage(content=cleaned or "Done.", tool_calls=response.tool_calls)
            else:
                # No real tool call happened at all — the model only wrote
                # fake text. Salvage it into a real tool call so the work
                # actually executes instead of silently doing nothing.
                fn_name, args_str = match.group(1), match.group(2)
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                if fn_name in TOOL_MAP:
                    response = AIMessage(
                        content="",
                        tool_calls=[{
                            "name": fn_name,
                            "args": args,
                            "id": f"salvaged-{uuid.uuid4().hex[:8]}",
                            "type": "tool_call",
                        }],
                    )

        content = response.content or ""
        suggestions = SUGGESTION_RE.findall(content)
        if suggestions and not getattr(response, "tool_calls", None):
            visible_text = SUGGESTION_RE.sub("", content).strip()
            response = AIMessage(content=visible_text)
            return {"messages": [response], "ai_suggested_follow_ups": suggestions[:3]}

        return {"messages": [response]}

    graph = StateGraph(InteractionState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    _compiled_graph = graph.compile(checkpointer=MemorySaver())
    return _compiled_graph
