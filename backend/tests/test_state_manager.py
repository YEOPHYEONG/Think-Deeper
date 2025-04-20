# tests/test_state_manager.py

import time
from datetime import timedelta, datetime
import pytest

# 프로젝트의 root가 PYTHONPATH에 들어가 있어야 합니다.
from backend.app.core import state_manager

def test_create_and_get_topic_and_state():
    topic = "테스트 주제"
    sid = state_manager.create_new_session(topic)
    # 생성 직후에는 state가 없음
    assert state_manager.get_session_autogen_state(sid) is None
    # topic 조회는 가능
    assert state_manager.get_session_topic(sid) == topic

def test_save_and_load_state():
    sid = state_manager.create_new_session("t2")
    mock_state = {"foo": "bar"}
    assert state_manager.save_session_autogen_state(sid, mock_state)
    # 저장한 상태가 그대로 반환되어야 함
    assert state_manager.get_session_autogen_state(sid) == mock_state

def test_delete_session():
    sid = state_manager.create_new_session("t3")
    assert state_manager.delete_session_state(sid) is True
    # 삭제 후엔 topic/state 모두 None
    assert state_manager.get_session_topic(sid) is None
    assert state_manager.get_session_autogen_state(sid) is None

def test_ttl_expiry():
    sid = state_manager.create_new_session("expire-test")
    # 강제로 생성 시간을 과거로 돌려 만료 유도
    state_manager._session_states[sid]["created_at"] = datetime.utcnow() - timedelta(hours=2)
    # 만료된 세션은 None 반환
    assert state_manager.get_session_topic(sid) is None
    assert state_manager.get_session_autogen_state(sid) is None

@pytest.mark.parametrize("n_threads", [5, 10])
def test_concurrent_access(n_threads):
    from concurrent.futures import ThreadPoolExecutor
    # 여러 스레드에서 create & delete 반복해도 에러 없어야 함
    def job():
        sid = state_manager.create_new_session("concurrent")
        state_manager.save_session_autogen_state(sid, {"x": 1})
        state_manager.get_session_autogen_state(sid)
        state_manager.delete_session_state(sid)
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        futures = [ex.submit(job) for _ in range(n_threads)]
        for f in futures:
            f.result()  # 에러 없으면 OK
