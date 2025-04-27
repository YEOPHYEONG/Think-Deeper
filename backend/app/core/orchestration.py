# backend/app/core/orchestration.py
import os
from typing import Optional, Dict, Any, List, Literal # Literal 추가

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END
from ..core.checkpointers import CombinedCheckpointer
from ..db.session import get_db_session
from ..core.config import get_settings

# 상태 모델은 기존 GraphState 사용 (Why 흐름 관련 필드는 여기에 추가하거나, 별도 상태 관리 필요)
from ..models.graph_state import GraphState
# state_manager 임포트는 초기 정보 로드 외에는 불필요해질 수 있음
from ..core import state_manager

# --- LangGraph 노드 함수 임포트 ---
from ..graph_nodes.coordinator import coordinator_node
from ..graph_nodes.critic import critic_node
from ..graph_nodes.moderator import moderator_node
from ..graph_nodes.search import search_node
# --- 기존 1:1 에이전트 노드 임포트 ---
from ..graph_nodes.advocate import advocate_node
from ..graph_nodes.socratic import socratic_node
# Why 관련 노드는 여기서 임포트하지 않음!
# from ..graph_nodes.sidekick import sidekick_node # Sidekick 구현 시 주석 해제

settings = get_settings()
db = get_db_session()
cp = CombinedCheckpointer(
    db_session=db,
    redis_url=settings.REDIS_URL,
    ttl=settings.SESSION_TTL_SECONDS,
)


# --- LangGraph 엣지 정의 ---
def should_continue(state: GraphState) -> str:
    """ Moderator 이후에는 항상 종료 """
    print("Edge: Moderator -> END")
    return END

def route_after_coordinator(state: GraphState) -> str:
    """ Coordinator 이후 라우팅 (Target Agent 기반) """
    if state.get("moderator_flags"):
        print("Edge: Coordinator -> Moderator (플래그)")
        return "moderator"
    target = state.get("target_agent", "critic") # 기본값 critic
    print(f"Edge: Coordinator -> Target: {target}")

    # --- 유효한 타겟 리스트 수정 ("why", "why_flow_start" 등 제거) ---
    valid_targets = ["critic", "advocate", "socratic"] # 이 그래프에서 직접 라우팅할 노드만 포함
    if target in valid_targets:
        print(f"Routing to: {target}")
        return target
    elif target == "why_flow_start":
         # 이 부분은 coordinator가 why_flow_start를 설정했을 때의 처리인데,
         # API 레벨에서 다른 오케스트레이션을 호출하기로 했으므로 여기서 처리할 필요 없음.
         # 만약 coordinator에서 여전히 why_flow_start를 설정한다면,
         # 이 그래프는 END로 가거나 특정 상태를 설정 후 종료해야 함.
         # 여기서는 일단 알 수 없는 타겟으로 간주하여 critic으로 보냄 (개선 필요)
         print(f"경고: 'why_flow_start' target 감지됨. 현재 그래프에서는 처리 불가. Critic으로 라우팅.")
         return "critic"
    else:
        print(f"경고: 알 수 없는 target_agent '{target}', critic으로 라우팅합니다.")
        return "critic" # 알 수 없는 타겟이면 기본 critic으로

def route_after_critic(state: GraphState) -> str:
    """ Critic 이후 라우팅 """
    if state.get("search_query"):
        print("Edge: Critic -> Search")
        return "search"
    else:
        print("Edge: Critic -> Moderator")
        return "moderator"

def route_after_one_on_one_agent(state: GraphState) -> str:
     """ 1:1 대화 에이전트 (Advocate, Socratic 등) 실행 후 라우팅 """
     # "Why"는 이 함수에서 처리될 필요 없음
     current_target = state.get('target_agent', 'Agent')
     print(f"Edge: {current_target.capitalize()} -> Moderator")
     return "moderator"

# --- LangGraph 그래프 구성 ---
# 상태 모델은 GraphState 사용 (Why 흐름 필드가 필요하면 여기에 병합 필요)
workflow = StateGraph(GraphState)

# 노드 추가 (why_node 제거 확인)
print("Defining Main Flow Graph: Adding nodes...")
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("search", search_node)
workflow.add_node("moderator", moderator_node)
workflow.add_node("advocate", advocate_node)
workflow.add_node("socratic", socratic_node)
# workflow.add_node("sidekick", sidekick_node) # Sidekick 구현 시 주석 해제
print("Nodes added.")

# 엣지 추가
print("Defining Main Flow Graph: Setting entry point and edges...")
workflow.set_entry_point("coordinator")

# Coordinator 이후 (why 관련 라우팅 제거)
workflow.add_conditional_edges(
    "coordinator",
    route_after_coordinator,
    { # 가능한 모든 타겟 노드 명시 (why 제거)
        "critic": "critic",
        "moderator": "moderator", # 플래그 감지 시
        "advocate": "advocate",
        "socratic": "socratic",
        # "sidekick": "sidekick",
    }
)

# Critic 이후
workflow.add_conditional_edges("critic", route_after_critic, {"search": "search", "moderator": "moderator"})
# Search 이후
workflow.add_edge("search", "critic") # 검색 후 다시 Critic으로

# --- 기존 1:1 에이전트 노드 이후 (why 관련 엣지 제거) ---
workflow.add_conditional_edges("advocate", route_after_one_on_one_agent, {"moderator": "moderator"})
# workflow.add_conditional_edges("why", ...) # <- 이 라인 삭제!
workflow.add_conditional_edges("socratic", route_after_one_on_one_agent, {"moderator": "moderator"})
# workflow.add_conditional_edges("sidekick", ...)

# Moderator 이후
workflow.add_conditional_edges("moderator", should_continue, {END: END})
print("Edges defined.")

# 그래프 컴파일
print("Compiling Main Flow Graph...")

db = get_db_session()
# `CombinedCheckpointer` 는 core/checkpointers.py 에 정의된 클래스를 사용
cp = CombinedCheckpointer(db_session=db,
                          redis_url=settings.REDIS_URL,
                          ttl=settings.SESSION_TTL_SECONDS)
checkpointer = cp
app_graph = workflow.compile(checkpointer=cp)

print("Main Flow Graph compiled successfully.")


# --- FastAPI 연동 함수 (변경 없음) ---
async def run_conversation_turn_langgraph(session_id: str, user_input: str) -> Optional[str]:
     """ LangGraph 대화 턴 실행 (기존 메인 그래프용) """
     # ... (이 함수 내용은 이전과 동일하게 유지) ...
     print(f"\n--- LangGraph Turn Start (Main Flow - Session: {session_id}) ---")
     print(f"User Input: '{user_input}'")
     config = {"configurable": {"thread_id": session_id}}
     graph_input = {"messages": [HumanMessage(content=user_input)]}

     # 상태 초기화 또는 복원 시 필요한 정보 주입
     current_state_checkpoint = checkpointer.get(config)
     if not current_state_checkpoint:
         print("세션 첫 턴, 초기 정보 설정 시도...")
         initial_info = state_manager.get_session_initial_info(session_id)
         if initial_info:
             graph_input["initial_topic"] = initial_info.get("topic", "주제 없음")
             graph_input["target_agent"] = initial_info.get("agent_type", "critic")
             graph_input["session_id"] = session_id
             # mode, critique_depth 등 GraphState에 정의된 필드 초기화
             # graph_input["mode"] = "OneOnOne" # 예시
             # graph_input["critique_depth"] = 50 # 예시
             # Why 흐름 관련 필드는 여기서 초기화하지 않음 (WhyGraphState 사용 시)
         else:
             print(f"경고: 세션 {session_id}의 초기 정보를 찾을 수 없습니다. 기본값 사용.")
             graph_input["initial_topic"] = "주제 없음"
             graph_input["target_agent"] = "critic"
             graph_input["session_id"] = session_id
             # graph_input["mode"] = "OneOnOne" # 예시
             # graph_input["critique_depth"] = 50 # 예시

     print("Graph Input (메시지 제외):", {k:v for k,v in graph_input.items() if k != 'messages'})

     try:
         async for event in app_graph.astream_events(graph_input, config=config, version="v1"):
             kind = event["event"]
             if kind == "on_graph_end": break

         final_state = app_graph.get_state(config=config)
         # 최종 상태 가져오기 실패 시 처리 추가
         if final_state is None or not hasattr(final_state, 'values'):
             print("Error: Failed to get final state from main graph.")
             return "(시스템 오류: 메인 그래프 최종 상태를 가져올 수 없습니다.)"

         final_state_values = final_state.values

         response = final_state_values.get("final_response")
         if response:
             print("최종 응답 반환 (final_response)")
             return response
         else: # Fallback
             messages = final_state_values.get("messages", [])
             if messages and isinstance(messages[-1], AIMessage):
                 print("최종 응답 반환 (마지막 AI 메시지)")
                 return messages[-1].content
             else:
                 error_msg = final_state_values.get('error_message', '알 수 없는 오류 또는 응답 없음')
                 print(f"최종 응답 반환 실패: {error_msg}")
                 return f"오류: {error_msg}"

     except Exception as e:
         import traceback; traceback.print_exc()
         return f"오류: 대화 처리 중 예외 발생 - {e}"