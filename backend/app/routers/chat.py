from fastapi import APIRouter, HTTPException

from ..langgraph_agent import get_agent_graph
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/interactions", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        graph = get_agent_graph()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke({"messages": [("user", req.message)]}, config=config)
    state = graph.get_state(config).values

    form_state = {k: v for k, v in state.items() if k != "messages"}
    return ChatResponse(reply=result["messages"][-1].content, form_state=form_state)
