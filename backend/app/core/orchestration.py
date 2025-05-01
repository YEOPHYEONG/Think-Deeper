# backend/app/core/orchestration.py

from typing import Optional, Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.db.session import async_session_factory
from app.core.redis_checkpointer import RedisCheckpointer
from app.core.sql_checkpointer import SQLCheckpointer
from app.core.checkpointers import CombinedCheckpointer
from app.models.graph_state import GraphState
from app.core import state_manager
from app.core.flush_manager import flush_session_to_postgres, mark_flush_failed, clear_flush_failed

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

workflow.add_conditional_edges(
    "coordinator",
    lambda s: "moderator" if s.get("moderator_flags") else (
        s.get("target_agent", "critic")
        if s.get("target_agent", "critic") in ["critic", "advocate", "socratic"]
        else "critic"
    ),
    {"critic": "critic", "moderator": "moderator", "advocate": "advocate", "socratic": "socratic"},
)
workflow.add_conditional_edges(
    "critic",
    lambda s: "search" if s.get("search_query") else "moderator",
    {"search": "search", "moderator": "moderator"},
)
workflow.add_edge("search", "critic")
workflow.add_conditional_edges("advocate", lambda _: "moderator", {"moderator": "moderator"})
workflow.add_conditional_edges("socratic", lambda _: "moderator", {"moderator": "moderator"})
workflow.add_conditional_edges("moderator", lambda _: END, {END: END})

# --- 그래프 컴파일 함수 ---
async def compile_graph() -> StateGraph:
    redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)
    sql_cp = SQLCheckpointer(async_session_factory)
    cp = CombinedCheckpointer(redis_cp, sql_cp)
    return workflow.compile(checkpointer=cp)

# --- FastAPI 연동 함수 ---
async def run_conversation_turn_langgraph(
    session_id: str,
    user_input: str
) -> Optional[str]:
    config = {"configurable": {"thread_id": session_id}}
    graph_input = {"messages": [HumanMessage(content=user_input)]}

    redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)
    async with async_session_factory() as db_session:
        sql_cp = SQLCheckpointer(async_session_factory)
        cp = CombinedCheckpointer(redis_cp, sql_cp)
        app_graph = workflow.compile(checkpointer=cp)

        state = await cp.aget(config)
        if state is None:
            info = await state_manager.get_session_initial_info(session_id)
            graph_input["session_id"] = session_id
            if info:
                graph_input["initial_topic"] = info.get("topic", "")
                graph_input["target_agent"] = info.get("agent_type", "critic")

        try:
            final_state = None
            async for ev in app_graph.astream_events(graph_input, config=config, version="v1"):
                print(f"[그래프 이벤트] {ev}")
                if ev.get("event") == "on_chain_end" and ev.get("name") == "LangGraph":
                    output_dict = ev["data"]["output"]

                    # ✅ dict인 값 중 가장 먼저 나오는 실제 상태(dict)를 final_state로 설정
                    if isinstance(output_dict, dict):
                        final_state = next(
                            (v for v in output_dict.values() if isinstance(v, dict)),
                            None
                        )
                    else:
                        final_state = output_dict  # fallback (예외적 상황)

                    print(f"[그래프 상태] final_state: {final_state}")

                    if final_state and isinstance(final_state, dict):
                        memory_state = final_state.get("memory", {})
                        messages = final_state.get("messages", [])
                        try:
                            await flush_session_to_postgres(session_id, memory_state, messages)
                            await clear_flush_failed(session_id)
                            print(f"[flush 성공] session_id={session_id}")
                        except Exception as flush_error:
                            print(f"[flush 실패] session_id={session_id}: {flush_error}")
                            await mark_flush_failed(session_id)
                    else:
                        print("[오류] final_state가 None이거나 dict가 아님")

                    break

            if final_state is None:
                return "(시스템 오류: 그래프 최종 상태를 가져올 수 없습니다.)"

            if not isinstance(final_state, dict):
                print("[오류] 최종 상태 포맷이 dict 아님")
                return "(시스템 오류: 그래프 최종 상태 형식이 올바르지 않습니다.)"

            vals = final_state
            if vals.get("final_response"):
                return vals["final_response"]

            msgs = vals.get("messages", [])
            if msgs and isinstance(msgs[-1], AIMessage):
                return msgs[-1].content

            return "(응답 없음)"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"(시스템 오류: {e})"
