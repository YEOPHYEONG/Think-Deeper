# backend/app/core/why_orchestration.py

from typing import List, Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from ..core.checkpointers import CombinedCheckpointer
from ..db.session import get_db_session
from ..core.config import get_settings
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage # 추가 임포트

# --- 상태 모델 임포트 ---
# 중요: 아래 모델은 실제로 app/models/ 에 정의되어 있어야 합니다!
# from ..models.why_graph_state import WhyGraphState # 예시 경로
# 임시로 기존 GraphState 사용 (WhyGraphState 정의 후 교체 필요)
from ..models.why_graph_state import WhyGraphState

# --- 노드 함수 임포트 ---
from ..graph_nodes.why.understand_idea_node import understand_idea_node
from ..graph_nodes.why.ask_motivation_why_node import ask_motivation_why_node
from ..graph_nodes.why.clarify_motivation_node import clarify_motivation_node
from ..graph_nodes.why.identify_assumptions_node import identify_assumptions_node
from ..graph_nodes.why.probe_assumption_node import probe_assumption_node

settings = get_settings()
db = get_db_session()
cp = CombinedCheckpointer(db_session=db,
                          redis_url=settings.REDIS_URL,
                          ttl=settings.SESSION_TTL_SECONDS)

# --- 조건부 라우팅 함수 정의 ---

def route_after_clarification(state: WhyGraphState) -> Literal["identify_assumptions", "clarify_motivation"]:
    """
    'Clarify Motivation' 노드 실행 후 라우팅 로직.
    동기가 명확해졌는지 상태를 확인하여 다음 노드를 결정합니다.
    """
    print("--- Routing: After Clarification ---")
    if state.get("motivation_clear", False):
        print("Decision: Motivation is clear -> Identify Assumptions")
        return "identify_assumptions"
    else:
        print("Decision: Motivation not clear -> Clarify Motivation (Loop back)")
        return "clarify_motivation"

def route_after_probing(state: WhyGraphState) -> Literal["probe_assumption", END]:
    """
    'Probe Assumption' 노드 실행 후 라우팅 로직.
    모든 가정을 탐색했는지 상태를 확인하여 반복 또는 종료를 결정합니다.
    """
    print("--- Routing: After Probing ---")
    if state.get("assumptions_fully_probed", False):
        print("Decision: All assumptions probed -> END")
        return END
    else:
        print("Decision: More assumptions to probe -> Probe Assumption (Loop back)")
        return "probe_assumption"

# --- 그래프 워크플로우 정의 ---
workflow = StateGraph(WhyGraphState)

# 1. 노드 추가
print("Defining Why Flow Graph: Adding nodes...")
workflow.add_node("understand_idea", understand_idea_node)
workflow.add_node("ask_motivation", ask_motivation_why_node)
workflow.add_node("clarify_motivation", clarify_motivation_node)
workflow.add_node("identify_assumptions", identify_assumptions_node)
workflow.add_node("probe_assumption", probe_assumption_node)
print("Nodes added.")

# 2. 엣지 및 시작점 설정
print("Defining Why Flow Graph: Setting entry point and edges...")
workflow.set_entry_point("understand_idea")

workflow.add_edge("understand_idea", "ask_motivation")
workflow.add_edge("ask_motivation", "clarify_motivation")

# 3. 조건부 엣지 설정
# Clarify Motivation 노드 이후: 동기 명확 여부에 따라 분기
workflow.add_conditional_edges(
    "clarify_motivation",
    route_after_clarification,
    {
        "identify_assumptions": "identify_assumptions", # 명확하면 가정 식별로
        "clarify_motivation": "clarify_motivation"      # 불명확하면 다시 명확화 질문으로 (루프)
    }
)

# Identify Assumptions 노드 이후: 항상 가정 탐색으로 이동
workflow.add_edge("identify_assumptions", "probe_assumption")

# Probe Assumption 노드 이후: 모든 가정 탐색 여부에 따라 분기
workflow.add_conditional_edges(
    "probe_assumption",
    route_after_probing,
    {
        END: END,                                  # 모든 가정 탐색 완료 시 종료
        "probe_assumption": "probe_assumption"     # 탐색할 가정 남았으면 다시 가정 탐색으로 (루프)
    }
)
print("Edges defined.")

# 4. 그래프 컴파일
print("Compiling Why Flow Graph...")
db = get_db_session()
# `CombinedCheckpointer` 는 core/checkpointers.py 에 정의된 클래스를 사용
cp = CombinedCheckpointer(db_session=db,
                          redis_url=settings.REDIS_URL,
                          ttl=settings.SESSION_TTL_SECONDS)

app_graph = workflow.compile(checkpointer=cp)

print("Why Flow Graph compiled successfully.")
        
# --- 5. 그래프 실행 함수 정의 (상세 구현) ---
async def run_why_exploration_turn(
    session_id: str,
    user_input: Optional[str] = None, # 사용자의 새 입력 (첫 턴 이후에는 답변)
    initial_topic: Optional[str] = None # 이 흐름을 시작할 때의 초기 주제/아이디어
    ) -> Optional[str]:
    """
    'Why 흐름' 오케스트레이션을 실행하는 메인 함수.
    세션 상태를 관리하고 그래프를 실행하며, AI의 다음 응답(주로 질문)을 반환합니다.
    """
    print(f"\n--- Running Why Exploration Turn (Session: {session_id}) ---")
    if user_input: print(f"User Input: '{user_input}'")
    if initial_topic: print(f"Initial Topic (if first turn): '{initial_topic}'")

    config = {"configurable": {"thread_id": session_id}}

    # --- 그래프 입력 구성 ---
    # 입력은 주로 messages 필드를 통해 전달됨
    graph_input: Dict[str, Any] = {}
    if user_input:
        graph_input["messages"] = [HumanMessage(content=user_input)]
    else:
        # 사용자 입력이 없는 경우 (예: 첫 턴 트리거 방식에 따라)
        # 빈 메시지 리스트 또는 다른 초기화 로직 필요 시 추가
        graph_input["messages"] = []
        print("Note: No direct user input provided for this turn.")


    # --- 첫 턴인지 확인하고 초기 상태 주입 (필요시) ---
    # 체크포인터를 사용하여 현재 세션의 상태를 가져옴
    current_state_checkpoint = checkpointer.get(config)
    if not current_state_checkpoint:
        print("세션 첫 턴, 초기 상태 설정...")
        # WhyGraphState에 정의된 기본값 외에 추가로 주입할 초기값 설정
        graph_input["session_id"] = session_id
        # 첫 턴에 사용자가 아이디어를 입력했다면, 그 아이디어가 처리될 것임
        # 만약 initial_topic을 상태로 전달해야 한다면 여기서 추가
        if initial_topic:
             graph_input["initial_topic"] = initial_topic
        # 다른 필수 초기값이 있다면 여기서 설정 (예: mode 등)
    else:
        print("기존 세션 상태 로드됨.")
        # 필요하다면 로드된 상태를 기반으로 graph_input 조정 가능

    print("Graph Input (메시지 제외):", {k:v for k,v in graph_input.items() if k != 'messages'})

    # --- 그래프 실행 및 결과 처리 ---
    final_response_content: Optional[str] = None
    try:
        print("Executing Why Flow Graph...")
        # 비동기 이벤트 스트리밍 방식으로 그래프 실행
        async for event in app_why_graph.astream_events(graph_input, config=config, version="v1"):
            kind = event["event"]
            # 디버깅용: 이벤트 종류 출력 (필요시 상세 내용 추가)
            # print(f"  Event: {kind}", f"| Data: {event['data']}")

            # 그래프 실행 완료 시 루프 종료
            if kind == "on_graph_end":
                print("Graph execution finished.")
                break
            # 필요시 특정 노드 시작/종료 시 로깅 등 추가 가능

        # 최종 상태 가져오기
        final_state = app_why_graph.get_state(config=config)
        final_state_values = final_state.values if hasattr(final_state, 'values') else {}

        # 최종 상태에서 사용자에게 전달할 응답 추출
        # 1) 모든 가정 탐색 완료 시 최우선으로 종료 메시지
        if final_state_values.get("assumptions_fully_probed"):
            final_response_content = (
                "모든 주요 가정을 살펴본 것 같습니다. "
                "이 과정이 아이디어를 명확히 하는 데 도움이 되었기를 바랍니다."
            )
            print("Final Response: All assumptions probed.")
        else:
            # 2) 그렇지 않으면 마지막 AI 메시지를 반환
            messages: List[BaseMessage] = final_state_values.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                final_response_content = messages[-1].content
                print(f"Final Response (Last AI Message): '{final_response_content[:100]}...'")
            else:
                # 3) 그 외 오류 처리
                error_msg = final_state_values.get("error_message")
                if error_msg:
                    print(f"Final State Error: {error_msg}")
                    final_response_content = f"(시스템 오류: {error_msg})"
                else:
                    print("Warning: Graph ended without a final AI message or known termination state.")
                    final_response_content = "(흐름이 예기치 않게 종료되었습니다.)"


    except Exception as e:
        error_msg = f"Why 흐름 실행 중 예외 발생: {e}"
        print(error_msg)
        import traceback; traceback.print_exc()
        final_response_content = f"(시스템 오류: {error_msg})"

    # 최종 응답 반환
    return final_response_content
