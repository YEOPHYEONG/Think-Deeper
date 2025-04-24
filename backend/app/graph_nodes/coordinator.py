# backend/app/graph_nodes/coordinator.py
from typing import Dict, Any, Optional
import re # 정규표현식 사용

# GraphState 모델 및 LangChain 메시지 타입 임포트
from ..models.graph_state import GraphState
from langchain_core.messages import HumanMessage, AIMessage

def coordinator_node(state: GraphState) -> Dict[str, Any]:
    """
    Coordinator 노드: 사용자 입력을 처리하고, 상태를 업데이트하며,
    명령어(/mode, /depth, /summarize)를 감지하고, 다음 실행할 노드를 결정합니다.
    또한 다음 Critic 턴을 위한 임시적인 현재 포커스를 설정합니다.
    """
    print("--- Coordinator Node 실행 ---")

    try:
        messages = state.get('messages', []) # 상태에 messages가 없을 경우 빈 리스트 사용
        if not messages:
            # 메시지가 없는 초기 상태일 수 있음 (첫 API 호출)
            # 이 경우, 세션 생성 시 설정된 초기 정보를 바탕으로 상태 설정 필요
            print("Coordinator: 메시지 리스트가 비어있음 (초기 상태)")
            # 초기 상태 설정 예시 (session_id, initial_topic 등 활용)
            initial_updates = {
                "mode": "Standard", # 기본 모드
                "nuance": "Debate",   # 기본 뉘앙스
                "critique_depth": 50, # 기본 깊이
                "moderator_flags": [],
                "error_message": None,
                "current_focus": state.get("initial_topic", "초기 주제") # 초기 주제를 포커스로
            }
            print(f"Coordinator: 초기 상태 설정 - {initial_updates}")
            return initial_updates

        # 마지막 메시지가 사용자 입력인지 확인
        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            # 마지막 메시지가 AI 응답 등 사용자 입력이 아닐 경우
            # (정상적인 흐름에서는 발생하기 어려우나 예외 처리)
            print("Coordinator: 경고 - 마지막 메시지가 HumanMessage 타입이 아님. 상태 업데이트 건너뜀.")
            # 현재 상태 유지 또는 특정 오류 상태 반환
            return {} # 빈 딕셔너리 반환하여 상태 변경 없음 표시

        user_input_content = last_message.content

        # 상태 업데이트 준비용 딕셔너리 (기존 상태 값으로 초기화)
        current_mode = state.get("mode", "Standard")
        current_nuance = state.get("nuance", "Debate") # 모드 변경 시 뉘앙스 조정 필요
        current_depth = state.get("critique_depth", 50)
        updates: Dict[str, Any] = {
            "mode": current_mode,
            "nuance": current_nuance,
            "critique_depth": current_depth,
            "moderator_flags": [], # 플래그 초기화
            "error_message": None, # 오류 메시지 초기화
            "current_focus": state.get("current_focus") # 기존 포커스 유지 또는 업데이트
        }
        command_detected = False # 명령어 처리 여부 플래그

        # --- 명령어 감지 및 처리 ---

        # 1. /summarize 명령어
        if "/summarize" in user_input_content.lower():
            print("Coordinator: /summarize 명령어 감지")
            updates["moderator_flags"].append("summarize_request")
            command_detected = True
            # 요약 요청 시 다른 명령어 처리는 건너뛸 수 있음

        # 명령어 처리가 요약이 아닐 경우 다른 명령어 확인
        if not command_detected:
            # 2. /mode 명령어 (정규표현식 사용)
            mode_match = re.search(r"/mode\s+(standard|fastdebate)", user_input_content, re.IGNORECASE)
            if mode_match:
                requested_mode = mode_match.group(1).lower()
                if requested_mode == "standard":
                    updates["mode"] = "Standard"
                    # 표준 모드로 변경 시 기본 뉘앙스 설정 (예: Debate)
                    updates["nuance"] = "Debate" # 또는 이전 뉘앙스 유지 등 정책 결정 필요
                    print(f"Coordinator: /mode standard 명령어 감지. Mode=Standard, Nuance=Debate 설정")
                elif requested_mode == "fastdebate":
                    updates["mode"] = "FastDebate"
                    updates["nuance"] = None # 빠른 모드에서는 뉘앙스 없음
                    print(f"Coordinator: /mode fastdebate 명령어 감지. Mode=FastDebate 설정")
                command_detected = True

            # 3. /depth 명령어 (정규표현식 사용)
            depth_match = re.search(r"/depth\s+(\d+)", user_input_content)
            if depth_match:
                try:
                    depth_val = int(depth_match.group(1))
                    # 입력값을 0에서 100 사이로 제한
                    validated_depth = max(0, min(100, depth_val))
                    # 현재 모드가 Standard일 때만 깊이 변경 허용 (선택적 정책)
                    if updates["mode"] == "Standard":
                        updates["critique_depth"] = validated_depth
                        print(f"Coordinator: /depth 명령어 감지. Depth={validated_depth} 설정")
                    else:
                        print("Coordinator: /depth 명령어 감지. 빠른 토론 모드에서는 Depth 변경 불가.")
                        # 사용자에게 알리는 메시지 추가 고려
                    command_detected = True
                except ValueError:
                    print("Coordinator: /depth 명령어 오류 - 유효하지 않은 숫자 값")
                    updates["error_message"] = "오류: /depth 명령어에 유효한 숫자를 입력해주세요 (0-100)."
                    # 오류 메시지를 사용자에게 전달하는 메커니즘 필요 (예: final_response 설정)

            # (구현 필요) 기타 명령어 처리...

        # --- 점진적 대화를 위한 현재 포커스 결정 ---
        if not command_detected and not updates.get("error_message"): # 명령어 없고 오류도 없을 때
             # TODO: 현재 포커스 결정 로직 개선 필요
             # 이전 메시지가 AI 메시지인지 확인
             if len(messages) > 1 and isinstance(messages[-2], AIMessage):
                  last_ai_message = messages[-2].content
                  # 임시 로직: 마지막 AI 메시지의 마지막 문장을 포커스로 간주
                  # 문장 분리 개선 필요 (마침표 외 다른 구두점 고려)
                  sentences = re.split(r'[.?!]\s*', last_ai_message)
                  non_empty_sentences = [s.strip() for s in sentences if s.strip()]
                  if non_empty_sentences:
                       # 마지막 문장이 너무 짧거나 단순하면 그 앞 문장 사용 등 로직 추가 가능
                       potential_focus = non_empty_sentences[-1]
                       if len(potential_focus) > 10: # 너무 짧지 않은 경우만 포커스로 설정 (임계값 조정 필요)
                            updates["current_focus"] = potential_focus
                            print(f"Coordinator: Current focus 설정 (임시) - '{updates['current_focus']}'")
                       else:
                            updates["current_focus"] = state.get("current_focus") # 이전 포커스 유지
                            print(f"Coordinator: 마지막 문장 짧음, 이전 포커스 유지 - '{updates['current_focus']}'")
                  else:
                       updates["current_focus"] = None # 포커스 설정 실패 시 초기화
                       print("Coordinator: 마지막 AI 메시지에서 포커스 추출 실패")
             else:
                  # 이전 AI 메시지가 없거나 다른 타입이면 포커스 초기화 또는 주제 유지
                  updates["current_focus"] = state.get("initial_topic", None) # 초기 주제 활용
                  print(f"Coordinator: 이전 AI 메시지 없음, 포커스 초기화/주제 유지 - '{updates['current_focus']}'")
        elif command_detected:
             # 명령어가 처리된 경우, 포커스를 유지할지 초기화할지 결정
             updates["current_focus"] = None # 예시: 명령어 처리 후 포커스 초기화
             print("Coordinator: 명령어 처리 후 포커스 초기화")


        # --- (선택적) 입력 포맷팅 ---
        # TODO: Formatting 노드/헬퍼 호출 로직 추가

        print(f"Coordinator: 상태 업데이트 반환 - Mode={updates['mode']}, Nuance={updates.get('nuance')}, Depth={updates['critique_depth']}, Flags={updates['moderator_flags']}, Focus={updates.get('current_focus')}, Error={updates.get('error_message')}")
        # 필요 없는 키 제거 (None 값 등)
        final_updates = {k: v for k, v in updates.items() if v is not None}
        return final_updates

    except Exception as e:
        error_msg = f"Coordinator 노드 심각한 오류 발생: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # 심각한 오류 시 오류 메시지만 포함하여 반환
        return {"error_message": error_msg}