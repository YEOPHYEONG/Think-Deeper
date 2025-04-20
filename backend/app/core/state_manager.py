# backend/app/core/state_manager.py
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# 세션 만료 TTL (1시간)
_SESSION_TTL = timedelta(hours=1)

# 상태를 저장할 인메모리 딕셔너리
# Key: session_id (str)
# Value: 세션 정보를 담는 딕셔너리:
#   {'session_id': str,
#    'initial_topic': str,
#    'created_at': datetime,
#    'autogen_state': Optional[Dict]}
# 주의: 서버 재시작 시 이 데이터는 초기화됩니다!
_session_states: Dict[str, Dict[str, Any]] = {}

# 전역 락으로 동시성 보호
_lock = threading.Lock()


def _is_expired(session_info: Dict[str, Any]) -> bool:
    """
    세션 정보가 TTL을 초과했는지 확인
    """
    return datetime.utcnow() - session_info.get("created_at", datetime.utcnow()) > _SESSION_TTL


def create_new_session(topic: str) -> str:
    """
    새로운 대화 세션 ID를 생성하고 초기 정보를 메모리에 저장한 뒤, 세션 ID를 반환합니다.
    AutoGen 상태는 아직 비어 있습니다 (None).
    """
    new_session_id = str(uuid.uuid4())
    session_info = {
        "session_id": new_session_id,
        "initial_topic": topic,
        "created_at": datetime.utcnow(),
        "autogen_state": None
    }
    with _lock:
        _session_states[new_session_id] = session_info
    print(f"세션 생성됨 (메모리): ID={new_session_id}, 주제='{topic}'")
    return new_session_id


def get_session_autogen_state(session_id: str) -> Optional[Dict[str, Any]]:
    """
    주어진 세션 ID에 해당하는 저장된 AutoGen 상태 딕셔너리를 반환합니다.
    세션이 없거나 만료되었으면 None을 반환합니다.
    """
    with _lock:
        session_info = _session_states.get(session_id)
        if not session_info or _is_expired(session_info):
            if session_info:
                # 만료된 세션 자동 삭제
                del _session_states[session_id]
                print(f"만료된 세션 삭제됨: ID={session_id}")
            else:
                print(f"세션 정보 로드 실패: ID={session_id} 찾을 수 없음")
            return None

        autogen_state = session_info.get("autogen_state")
        if autogen_state is not None:
            print(f"AutoGen 상태 로드됨 (메모리): ID={session_id}")
            return autogen_state
        else:
            print(f"AutoGen 상태 아직 없음 (메모리): ID={session_id}")
            return None


def save_session_autogen_state(session_id: str, autogen_state: Dict[str, Any]) -> bool:
    """
    주어진 세션 ID에 해당하는 AutoGen 상태 딕셔너리를 메모리에 저장(업데이트)합니다.
    성공하면 True, 세션이 없거나 만료된 경우 False를 반환합니다.
    """
    with _lock:
        session_info = _session_states.get(session_id)
        if not session_info or _is_expired(session_info):
            if session_info:
                del _session_states[session_id]
                print(f"만료된 세션 삭제됨: ID={session_id}")
            else:
                print(f"세션 정보 저장 실패: ID={session_id} 찾을 수 없음")
            return False

        session_info["autogen_state"] = autogen_state
        print(f"AutoGen 상태 저장됨 (메모리): ID={session_id}")
        return True


def get_session_topic(session_id: str) -> Optional[str]:
    """세션 ID로 해당 세션의 초기 주제를 가져옵니다. 만료된 세션은 None 반환."""
    with _lock:
        session_info = _session_states.get(session_id)
        if not session_info or _is_expired(session_info):
            if session_info:
                del _session_states[session_id]
                print(f"만료된 세션 삭제됨: ID={session_id}")
            else:
                print(f"세션 주제 로드 실패: ID={session_id} 찾을 수 없음")
            return None
        return session_info.get("initial_topic")


def delete_session_state(session_id: str) -> bool:
    """세션 상태 정보 전체를 메모리에서 제거합니다."""
    with _lock:
        if session_id in _session_states:
            del _session_states[session_id]
            print(f"세션 상태 삭제됨 (메모리): ID={session_id}")
            return True
        print(f"세션 상태 삭제 실패 (메모리): ID={session_id} 찾을 수 없음")
        return False
