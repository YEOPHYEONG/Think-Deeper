# backend/app/core/orchestration.py
import os
from typing import Optional, Dict, Any, List

# LangChain 및 LangGraph 관련 임포트
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage # BaseMessage 추가
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # 인메모리 상태 저장용

# 프로젝트 내부 모듈 임포트
from ..core.config import get_settings
from ..models.graph_state import GraphState # 정의한 상태 모델 임포트

# --- LangGraph 노드 함수 임포트 ---
# 각 노드의 상세 로직은 해당 파일에 구현되어 있다고 가정합니다.
from ..graph_nodes.coordinator import coordinator_node
from ..graph_nodes.critic import critic_node
from ..graph_nodes.moderator import moderator_node
from ..graph_nodes.search import search_node
# from ..graph_nodes.formatting import formatting_node # 필요시 추가

settings = get_settings()

# --- 모델 클라이언트 설정 (필요시 graph_nodes와 공유하는 방식 고려) ---
# 예시: 여러 모델을 필요에 따라 로드하도록 구성 가능
# 상세 설계 IV.D (동적 LLM 라우팅)를 반영하여 개선 필요
llm_high_perf = ChatOpenAI(model="gpt-4o", temperature=0.7, api_key=settings.OPENAI_API_KEY)
llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=settings.OPENAI_API_KEY) # 빠른 모델 예시

# --- LangGraph 엣지 (흐름 제어) 로직 ---
# (엣지 로직 함수들은 orchestration에 두는 것이 일반적일 수 있음)

def should_continue(state: GraphState) -> str:
    """워크플로우를 계속할지 종료할지 결정"""
    # 간단한 예시: 특정 조건(예: 사용자 입력이 '끝')이면 종료
    # 실제로는 더 복잡한 종료 조건 필요 (예: 최대 턴 수, 특정 상태)
    # 사용자 입력은 보통 messages 리스트의 마지막에서 두 번째 항목일 수 있음 (마지막은 AI 응답)
    if len(state['messages']) >= 2:
        last_user_message = state['messages'][-2]
        if isinstance(last_user_message, HumanMessage) and last_user_message.content.lower() == "끝":
            print("Edge: 종료 조건 충족")
            return END
    print("Edge: 계속 진행 (다음 턴 대기)")
    # FastAPI 연동 시, 이 턴은 여기서 끝나고 사용자 입력을 다시 받게 되므로 END로 처리
    return END


def route_after_coordinator(state: GraphState) -> str:
    """Coordinator 이후 라우팅 결정"""
    if state.get("moderator_flags"):
        print("Edge: Coordinator -> Moderator (플래그 감지)")
        return "moderator"
    else:
        # TODO: Formatting 노드 필요 여부 판단 로직 추가
        print("Edge: Coordinator -> Critic")
        return "critic"


def route_after_critic(state: GraphState) -> str:
    """Critic 이후 라우팅 결정"""
    if state.get("search_query"):
        print("Edge: Critic -> Search (검색 요청)")
        return "search"
    else:
        # TODO: Moderator 검토 단계 포함 여부 결정
        print("Edge: Critic -> Moderator (검토/출력 준비)")
        return "moderator"


# --- LangGraph 그래프 구성 ---

workflow = StateGraph(GraphState)

# 노드 추가 (임포트한 함수 사용)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("search", search_node)
workflow.add_node("moderator", moderator_node)
# TODO: Formatting 노드 추가

# 엣지 추가
workflow.set_entry_point("coordinator") # 시작점

# Coordinator 이후 라우팅
workflow.add_conditional_edges(
    "coordinator",
    route_after_coordinator,
    {
        "critic": "critic",
        "moderator": "moderator",
        # "formatting_input": "formatting_input" # Formatting 노드 추가시
    }
)

# Critic 이후 라우팅
workflow.add_conditional_edges(
    "critic",
    route_after_critic,
    {
        "search": "search",
        "moderator": "moderator",
    }
)

# Search 이후 Critic으로 돌아감
workflow.add_edge("search", "critic")

# Moderator 이후 종료 또는 계속
workflow.add_conditional_edges(
    "moderator",
    should_continue, # 현재 로직상 항상 END로 감 (API 응답 후 종료)
    {
        END: END,
        # "continue_flow": ??? # 웹소켓 등 연속적인 연결이 아니면 필요 없음
    }
)

# 그래프 컴파일 및 메모리 설정
# MemorySaver는 간단한 인메모리 저장소. 실제 운영 시 DB 기반 Checkpointer 사용 고려
checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)


# --- FastAPI 와 연동할 메인 함수 ---

async def run_conversation_turn_langgraph(session_id: str, user_input: str) -> Optional[str]:
    """
    LangGraph를 사용하여 대화 턴을 실행합니다. (최종 상태 가져오기 방식 수정)
    """
    print(f"\n--- LangGraph Turn Start (Session: {session_id}) ---")
    print(f"User Input: '{user_input}'")

    # LangGraph 실행을 위한 설정 (세션 ID 사용)
    config = {"configurable": {"thread_id": session_id}}

    # 사용자 입력을 GraphState 형식으로 변환하여 입력
    # 중요: 이전 상태를 로드하여 messages를 누적해야 함 (MemorySaver가 처리)
    graph_input = {"messages": [HumanMessage(content=user_input)]}
    print("Graph Input:", graph_input) # 디버깅용 입력 출력

    try:
        # astream_events를 사용하여 그래프 실행 및 로깅
        async for event in app_graph.astream_events(graph_input, config=config, version="v1"):
            kind = event["event"]
            # print(f"Event: {kind}, Data: {event['data']}") # 모든 이벤트 로깅 (디버깅 시 유용)

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # Optional: print LLM tokens as they stream
                    # print(content, end="", flush=True) # 스트리밍 출력
                    pass
            elif kind == "on_tool_start":
                print("\n--")
                print(f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}")
            elif kind == "on_tool_end":
                print(f"Ended tool: {event['name']}")
                # print(f"Tool output was: {event['data'].get('output')}") # 너무 길 수 있음
                print("--")
            elif kind == "on_graph_end":
                 print("\n--- Graph Execution Finished (Events Loop) ---")
                 # 루프 종료 조건으로만 사용, 여기서 상태 추출 안 함
                 break

        # !!! 중요: 루프 종료 후 get_state로 최종 상태 명시적 조회 !!!
        print("Retrieving final state using get_state...")
        final_state = app_graph.get_state(config=config)

        # 최종 상태와 그 안의 values 타입을 확인 (디버깅)
        print("Final State retrieved (type):", type(final_state)) # Checkpoint 객체 타입 확인

        # Checkpoint 객체에서 실제 상태 값(values) 추출
        if hasattr(final_state, 'values'):
             final_state_values = final_state.values # values는 상태 딕셔너리여야 함
             print("Final State Values (type):", type(final_state_values))
             if isinstance(final_state_values, dict):
                   print("Final State Keys:", final_state_values.keys()) # 상태 키 확인
                   # 최종 상태에서 응답 추출
                   critic_response = final_state_values.get("final_response")
                   if critic_response:
                       print(f"\nFinal Response: {critic_response}")
                       return critic_response
                   else:
                       # final_response가 없다면, 마지막 AI 메시지를 반환 시도
                       messages = final_state_values.get("messages", [])
                       print("Messages in final state (count):", len(messages)) # 메시지 개수 확인
                       if messages and isinstance(messages[-1], AIMessage):
                            last_ai_message = messages[-1].content
                            print(f"\nFinal Response (Fallback from last AI message): {last_ai_message}")
                            return last_ai_message
                       else:
                           error_msg = final_state_values.get("error_message", "최종 응답(final_response) 또는 마지막 AI 메시지를 상태에서 찾을 수 없습니다.")
                           print(f"Error: {error_msg}")
                           return f"오류: {error_msg}"
             else:
                  error_msg = "최종 상태의 'values'가 딕셔너리 형태가 아닙니다."
                  print(f"Error: {error_msg} (Type: {type(final_state_values)})")
                  return f"오류: 최종 상태 형식 오류 ({error_msg})."
        else:
             error_msg = "get_state 결과에서 'values' 속성을 찾을 수 없습니다."
             print(f"Error: {error_msg} (Object: {final_state})")
             return f"오류: 최종 상태 형식 오류 ({error_msg})."

    except Exception as e:
        import traceback
        print(f"LangGraph 실행 또는 상태 조회 중 오류 발생: {e}")
        traceback.print_exc()
        # 오류 발생 시에도 상태 확인 시도 (디버깅 목적)
        try:
             current_state = app_graph.get_state(config)
             print("State at time of error:", current_state)
        except Exception as state_e:
             print("Could not retrieve state after error:", state_e)
        return f"오류: 대화 처리 중 예외 발생 - {e}"

# --- 기존 AutoGen 관련 코드 주석 처리 또는 삭제 ---
# async def run_conversation_turn(...):
# def get_model_client(...):