# backend/app/core/orchestration.py
import os
from typing import Optional, Dict, Any, List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # 또는 DB 체크포인터

from ..core.config import get_settings
from ..models.graph_state import GraphState
from ..core import state_manager # 초기 정보 로드용 (임시)

# --- LangGraph 노드 함수 임포트 ---
from ..graph_nodes.coordinator import coordinator_node
from ..graph_nodes.critic import critic_node
from ..graph_nodes.moderator import moderator_node
from ..graph_nodes.search import search_node
# --- 신규 노드 임포트 ---
from ..graph_nodes.advocate import advocate_node
from ..graph_nodes.why import why_node
from ..graph_nodes.socratic import socratic_node
# from ..graph_nodes.sidekick import sidekick_node # Sidekick 구현 시 주석 해제

settings = get_settings()
# --- LLM 초기화 제거됨 ---

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
    print(f"Edge: Coordinator -> {target.capitalize()} (Target: {target})")
    # --- 유효한 타겟 리스트 업데이트 ---
    valid_targets = ["critic", "advocate", "why", "socratic"] # 구현된 노드 이름들
    if target in valid_targets:
        return target
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
     """ 1:1 대화 에이전트 (Advocate, Why, Socratic 등) 실행 후 라우팅 """
     # TODO: 이 에이전트들도 필요시 Search 요청 등을 할 수 있도록 확장 가능
     print(f"Edge: {state.get('target_agent', 'Agent').capitalize()} -> Moderator")
     return "moderator"

# --- LangGraph 그래프 구성 ---
workflow = StateGraph(GraphState)

# 노드 추가
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("search", search_node)
workflow.add_node("moderator", moderator_node)
# --- 신규 노드 추가 ---
workflow.add_node("advocate", advocate_node)
workflow.add_node("why", why_node)
workflow.add_node("socratic", socratic_node)
# workflow.add_node("sidekick", sidekick_node) # Sidekick 구현 시 주석 해제

# 엣지 추가
workflow.set_entry_point("coordinator")

# Coordinator 이후
workflow.add_conditional_edges(
    "coordinator",
    route_after_coordinator,
    { # 가능한 모든 타겟 노드 명시
        "critic": "critic",
        "moderator": "moderator", # 플래그 감지 시
        # --- 신규 노드 라우팅 추가 ---
        "advocate": "advocate",
        "why": "why",
        "socratic": "socratic",
        # "sidekick": "sidekick", # Sidekick 구현 시 주석 해제
    }
)

# Critic 이후
workflow.add_conditional_edges("critic", route_after_critic, {"search": "search", "moderator": "moderator"})
# Search 이후
workflow.add_edge("search", "critic") # 검색 후 다시 Critic으로

# --- 신규 1:1 에이전트 노드 이후 ---
workflow.add_conditional_edges("advocate", route_after_one_on_one_agent, {"moderator": "moderator"})
workflow.add_conditional_edges("why", route_after_one_on_one_agent, {"moderator": "moderator"})
workflow.add_conditional_edges("socratic", route_after_one_on_one_agent, {"moderator": "moderator"})
# workflow.add_conditional_edges("sidekick", route_after_one_on_one_agent, {"moderator": "moderator"}) # Sidekick 구현 시

# Moderator 이후
workflow.add_conditional_edges("moderator", should_continue, {END: END})

# 그래프 컴파일
checkpointer = MemorySaver() # TODO: DB 기반 체크포인터 고려
app_graph = workflow.compile(checkpointer=checkpointer)

# --- FastAPI 연동 함수 ---
async def run_conversation_turn_langgraph(session_id: str, user_input: str) -> Optional[str]:
     """ LangGraph 대화 턴 실행 (상태 초기화 로직 개선) """
     print(f"\n--- LangGraph Turn Start (Session: {session_id}) ---")
     print(f"User Input: '{user_input}'")
     config = {"configurable": {"thread_id": session_id}}

     # --- 그래프 입력 구성 ---
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
             graph_input["mode"] = "OneOnOne"
             graph_input["critique_depth"] = 50 # Critic 외 에이전트도 사용할 수 있으니 기본값 유지
         else:
             print(f"경고: 세션 {session_id}의 초기 정보를 찾을 수 없습니다. 기본값 사용.")
             # 기본값 설정 (변경 없음)
             graph_input["initial_topic"] = "주제 없음"
             graph_input["target_agent"] = "critic"
             graph_input["session_id"] = session_id
             graph_input["mode"] = "OneOnOne"
             graph_input["critique_depth"] = 50

     print("Graph Input (메시지 제외):", {k:v for k,v in graph_input.items() if k != 'messages'})

     # --- 그래프 실행 및 결과 처리 (변경 없음) ---
     try:
         async for event in app_graph.astream_events(graph_input, config=config, version="v1"):
             kind = event["event"]
             if kind == "on_graph_end": break

         final_state = app_graph.get_state(config=config)
         final_state_values = final_state.values if hasattr(final_state, 'values') else {}

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