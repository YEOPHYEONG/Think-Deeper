# backend/app/core/orchestration.py

from typing import Optional, Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.db.session import async_session_factory
from app.core.checkpointers import CombinedCheckpointer
from app.models.graph_state import GraphState
from app.core import state_manager

# --- 노드 임포트 ---
from app.graph_nodes.coordinator import coordinator_node
from app.graph_nodes.critic import critic_node
from app.graph_nodes.moderator import moderator_node
from app.graph_nodes.search import search_node
from app.graph_nodes.advocate import advocate_node
from app.graph_nodes.socratic import socratic_node

# --- 그래프 정의 ---
workflow = StateGraph(GraphState)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("search", search_node)
workflow.add_node("moderator", moderator_node)
workflow.add_node("advocate", advocate_node)
workflow.add_node("socratic", socratic_node)
workflow.set_entry_point("coordinator")

# Coordinator → (critic/advocate/socratic/moderator)
workflow.add_conditional_edges(
    "coordinator",
    lambda s: "moderator" if s.get("moderator_flags") else (
        s.get("target_agent", "critic")
        if s.get("target_agent", "critic") in ["critic","advocate","socratic"]
        else "critic"
    ),
    {"critic":"critic","moderator":"moderator","advocate":"advocate","socratic":"socratic"},
)
workflow.add_conditional_edges(
    "critic",
    lambda s: "search" if s.get("search_query") else "moderator",
    {"search":"search","moderator":"moderator"},
)
workflow.add_edge("search", "critic")
workflow.add_conditional_edges("advocate", lambda _: "moderator", {"moderator":"moderator"})
workflow.add_conditional_edges("socratic", lambda _: "moderator", {"moderator":"moderator"})
workflow.add_conditional_edges("moderator", lambda _: END, {END: END})

# 체크포인터 생성 및 그래프 컴파일
cp = CombinedCheckpointer(
    async_session_factory,         # DB 세션 팩토리
    settings.REDIS_URL,            # Redis URL
    settings.SESSION_TTL_SECONDS,  # TTL (초)
)
app_graph = workflow.compile(checkpointer=cp)

# --- FastAPI 연동 함수 ---
async def run_conversation_turn_langgraph(
    session_id: str,
    user_input: str
) -> Optional[str]:
    config = {"configurable": {"thread_id": session_id}}
    graph_input = {"messages": [HumanMessage(content=user_input)]}

    # 첫 메시지일 때 초기 정보 주입
    state = await cp.aget(config)
    if state is None:
        info = state_manager.get_session_initial_info(session_id)
        graph_input["session_id"] = session_id
        if info:
            graph_input["initial_topic"] = info.get("topic", "")
            graph_input["target_agent"] = info.get("agent_type", "critic")

    try:
        async for ev in app_graph.astream_events(graph_input, config=config, version="v1"):
            if ev.get("event") == "on_graph_end":
                break

        final = app_graph.get_state(config=config)
        if final is None or not hasattr(final, "values"):
            return "(시스템 오류: 그래프 최종 상태를 가져올 수 없습니다.)"

        vals = final.values
        # final_response 우선
        if vals.get("final_response"):
            return vals["final_response"]
        # 아니면 마지막 AIMessage
        msgs = vals.get("messages", [])
        if msgs and isinstance(msgs[-1], AIMessage):
            return msgs[-1].content

        return "(응답 없음)"
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"(오류: {e})"