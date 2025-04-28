# backend/app/core/why_orchestration.py

from typing import List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.core.redis_checkpointer import RedisCheckpointer
from app.core.sql_checkpointer import SQLCheckpointer
from app.core.checkpointers import CombinedCheckpointer
from app.db.session import async_session_factory
from app.core.config import get_settings
from app.models.why_graph_state import WhyGraphState

from app.graph_nodes.why.understand_idea_node import understand_idea_node
from app.graph_nodes.why.ask_motivation_why_node import ask_motivation_why_node
from app.graph_nodes.why.clarify_motivation_node import clarify_motivation_node
from app.graph_nodes.why.identify_assumptions_node import identify_assumptions_node
from app.graph_nodes.why.probe_assumption_node import probe_assumption_node

settings = get_settings()

# --- LangGraph Workflow 구성 ---

def route_after_clarification(state: WhyGraphState) -> str:
    return "identify_assumptions" if state.get("motivation_clear", False) else "clarify_motivation"

def route_after_probing(state: WhyGraphState) -> str:
    return END if state.get("assumptions_fully_probed", False) else "probe_assumption"

workflow = StateGraph(WhyGraphState)
workflow.add_node("understand_idea", understand_idea_node)
workflow.add_node("ask_motivation", ask_motivation_why_node)
workflow.add_node("clarify_motivation", clarify_motivation_node)
workflow.add_node("identify_assumptions", identify_assumptions_node)
workflow.add_node("probe_assumption", probe_assumption_node)

workflow.set_entry_point("understand_idea")

workflow.add_edge("understand_idea", "ask_motivation")
workflow.add_edge("ask_motivation", "clarify_motivation")
workflow.add_conditional_edges("clarify_motivation", route_after_clarification, {
    "identify_assumptions": "identify_assumptions",
    "clarify_motivation": "clarify_motivation",
})
workflow.add_edge("identify_assumptions", "probe_assumption")
workflow.add_conditional_edges("probe_assumption", route_after_probing, {
    END: END,
    "probe_assumption": "probe_assumption",
})

app_why_graph = workflow.compile()

# --- 그래프 실행 함수 ---

async def run_why_exploration_turn(
    session_id: str,
    user_input: Optional[str] = None,
    initial_topic: Optional[str] = None
) -> Optional[str]:
    config = {"configurable": {"thread_id": session_id}}
    graph_input: Dict[str, Any] = {}

    if user_input:
        graph_input["messages"] = [HumanMessage(content=user_input)]
    else:
        graph_input["messages"] = []

    async with async_session_factory() as session:
        redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)
        sql_cp = SQLCheckpointer(session)
        checkpointer = CombinedCheckpointer(redis_cp, sql_cp)

        current_state_checkpoint = await checkpointer.aget(session_id)
        if not current_state_checkpoint:
            graph_input["session_id"] = session_id
            if initial_topic:
                graph_input["initial_topic"] = initial_topic

        try:
            async for event in app_why_graph.astream_events(graph_input, config=config, checkpointer=checkpointer):
                if event["event"] == "on_graph_end":
                    break

            final_state = app_why_graph.get_state(config=config)
            if final_state is None or not hasattr(final_state, "values"):
                return "(시스템 오류: Why 그래프 최종 상태를 가져올 수 없습니다.)"

            final_values = final_state.values

            if final_values.get("assumptions_fully_probed"):
                return "모든 주요 가정을 살펴본 것 같습니다. 도움이 되었기를 바랍니다."
            else:
                messages: List[BaseMessage] = final_values.get("messages", [])
                if messages and isinstance(messages[-1], AIMessage):
                    return messages[-1].content
                else:
                    error_msg = final_values.get("error_message", "알 수 없는 오류")
                    return f"오류: {error_msg}"

        except Exception as e:
            import traceback; traceback.print_exc()
            return f"오류: Why 흐름 처리 중 예외 발생 - {e}"
