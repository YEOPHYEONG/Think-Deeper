# backend/app/core/why_orchestration.py

from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphInterrupt
from langgraph.types import Interrupt as TypesInterrupt # 명시적으로 langgraph.types.Interrupt 사용
from langgraph.checkpoint.memory import MemorySaver
import copy
import asyncio
import traceback

from app.core.llm_provider import get_high_performance_llm
from app.core.user_state import UserStateStore
from app.db.session import async_session_factory
from app.core.config import get_settings
from app.models.why_graph_state import WhyGraphState
from app.graph_nodes.why.motivation_elicitation_node import motivation_elicitation_node
# 다른 노드들도 interrupt 시 value에 상태 dict를 전달하도록 수정 필요할 수 있음
from app.graph_nodes.why.summarize_idea_motivation_node import summarize_idea_motivation_node
from app.graph_nodes.why.identify_assumptions_node import identify_assumptions_node
from app.graph_nodes.why.probe_assumption_node import probe_assumption_node
from app.graph_nodes.why.findings_summarization_node import findings_summarization_node
from app.graph_nodes.why.free_conversation_node import free_conversation_node

settings = get_settings()
checkpointer = MemorySaver()
print("[Orchestrator Setup] Using MemorySaver for LangGraph's internal checkpointing.")
user_store = UserStateStore(async_session_factory)

app_why_graph = None
# (Graph Definition and Compilation - 이전과 동일하게 유지)
if checkpointer is not None:
    try:
        workflow = StateGraph(WhyGraphState)
        workflow.add_node("motivation_elicitation", motivation_elicitation_node)
        workflow.add_node("summarize_idea_motivation", summarize_idea_motivation_node)
        workflow.add_node("identify_assumptions", identify_assumptions_node)
        workflow.add_node("probe_assumption", probe_assumption_node)
        workflow.add_node("findings_summarization", findings_summarization_node)
        workflow.add_node("free_conversation", free_conversation_node)
        workflow.set_entry_point("motivation_elicitation")

        def decide_after_motivation(state: WhyGraphState) -> str:
            motivation_cleared = state.get("motivation_cleared", False)
            # motivation_elicitation_node가 interrupt 대신 상태를 반환하는 경우,
            # 이 엣지는 해당 상태를 기반으로 다음 노드를 결정합니다.
            # 만약 interrupt가 발생했다면, ainvoke는 중단된 상태를 반환하고 이 엣지는 실행되지 않습니다.
            # 오케스트레이터가 interrupt를 처리하고 사용자에게 응답을 전달합니다.
            print(f"  [COND_EDGE] decide_after_motivation: motivation_cleared={motivation_cleared}")
            if motivation_cleared: # 노드가 명확하다고 판단하여 상태를 반환한 경우
                return "summarize_idea_motivation"
            # 노드가 interrupt를 발생시켰거나, 명확하지 않다고 판단하여 특정 키 없이 상태를 반환한 경우
            # (현재 motivation_elicitation_node는 명확하지 않으면 항상 interrupt 발생)
            print(f"  [COND_EDGE][WARN] decide_after_motivation: motivation not cleared or node interrupted, ending graph run for this turn.")
            return END # 현재 턴 종료, 오케스트레이터가 interrupt 처리

        def decide_after_summary(state: WhyGraphState) -> str:
            idea_summary_exists = bool(state.get("idea_summary", "").strip())
            motivation_summary_exists = bool(state.get("motivation_summary", "").strip()) or bool(state.get("final_motivation_summary", "").strip())
            print(f"  [COND_EDGE] decide_after_summary: idea_summary_exists={idea_summary_exists}, motivation_summary_exists={motivation_summary_exists}")
            if idea_summary_exists and motivation_summary_exists:
                 return "identify_assumptions"
            print(f"  [COND_EDGE][WARN] decide_after_summary: Missing summary, ending.")
            return END

        def decide_after_identification(state: WhyGraphState) -> str:
            assumptions_identified = bool(state.get("identified_assumptions"))
            print(f"  [COND_EDGE] decide_after_identification: assumptions_identified={assumptions_identified}")
            if assumptions_identified:
                return "probe_assumption"
            return "findings_summarization"

        def decide_after_probing(state: WhyGraphState) -> str:
            all_probed = state.get("assumptions_fully_probed", False)
            print(f"  [COND_EDGE] decide_after_probing: assumptions_fully_probed={all_probed}")
            if all_probed:
                return "findings_summarization"
            print(f"  [COND_EDGE][WARN] decide_after_probing: assumptions not fully probed, expecting interrupt or ending.")
            return END

        def decide_after_findings(state: WhyGraphState) -> str:
            findings_summary_exists = bool(state.get("findings_summary", "").strip())
            print(f"  [COND_EDGE] decide_after_findings: findings_summary_exists={findings_summary_exists}")
            return "free_conversation" if findings_summary_exists else END

        workflow.add_conditional_edges("motivation_elicitation", decide_after_motivation, {
            "summarize_idea_motivation": "summarize_idea_motivation", END: END
        })
        workflow.add_conditional_edges("summarize_idea_motivation", decide_after_summary, {
            "identify_assumptions": "identify_assumptions", END: END
        })
        workflow.add_conditional_edges("identify_assumptions", decide_after_identification, {
            "probe_assumption": "probe_assumption", "findings_summarization": "findings_summarization"
        })
        workflow.add_conditional_edges("probe_assumption", decide_after_probing, {
            "findings_summarization": "findings_summarization", END: END
        })
        workflow.add_conditional_edges("findings_summarization", decide_after_findings, {
            "free_conversation": "free_conversation", END: END
        })
        workflow.add_edge("free_conversation", END)

        app_why_graph = workflow.compile(checkpointer=checkpointer)
        print("[Orchestrator Setup] Graph compiled successfully.")
    except Exception as e_compile:
        print(f"[Orchestrator Setup][ERROR] Failed to compile graph: {e_compile}")
        traceback.print_exc()
        app_why_graph = None
else:
    print("[Orchestrator Setup][ERROR] Cannot compile graph: Checkpointer is None.")


def _serialize_state_for_db(state: Dict[str, Any]) -> Dict[str, Any]:
    # ... (이전과 동일)
    if not isinstance(state, dict): return {}
    serializable_state = {}
    keys_to_exclude = {'__interrupt__', 'parent_config', 'pending_writes', 'pending_sends',
                       'channel_values', 'versions_seen', 'metadata', 'configurable'}
    for key, value in state.items():
        if key in keys_to_exclude: continue
        if key == 'messages':
            serializable_messages = []
            if isinstance(value, list):
                for msg in value:
                    if isinstance(msg, BaseMessage):
                        serializable_messages.append({
                            "type": msg.type, "content": msg.content,
                            "additional_kwargs": getattr(msg, 'additional_kwargs', {})
                        })
                    elif isinstance(msg, dict) and "type" in msg and "content" in msg:
                         serializable_messages.append(msg)
            serializable_state[key] = serializable_messages
        elif isinstance(value, (str, int, float, bool, type(None), list, dict)):
             serializable_state[key] = value
    return serializable_state

async def run_why_exploration_turn(
    session_id: str,
    user_input: Optional[str] = None,
    initial_topic: Optional[str] = None
) -> Optional[str]:
    # ... (함수 시작, 상태 로드, graph_input 초기화 로직은 이전과 동일하게 유지) ...
    if not app_why_graph:
         print("[ERROR Orchestrator] Graph is not compiled!")
         raise HTTPException(status_code=500, detail="Graph is not compiled or unavailable.")

    print(f"[DEBUG Orchestrator] --- Starting Turn --- Session: {session_id}")
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}
    graph_input: Dict[str, Any] = {}

    is_first_turn_of_session = False
    current_state_from_store = await user_store.load(session_id) or {}
    print(f"  [DEBUG Orchestrator] Loaded state from UserStore for session {session_id} (keys: {list(current_state_from_store.keys())})")
    print(f"  [DEBUG Orchestrator] 'has_asked_initial' from UserStore: {current_state_from_store.get('has_asked_initial')}")

    if user_input is not None:
        if not current_state_from_store:
            print(f"  [WARN Orchestrator] No state found for {session_id}, but input present. Treating as first turn.")
            if not initial_topic: initial_topic = user_input
            is_first_turn_of_session = True
        else:
            graph_input = copy.deepcopy(current_state_from_store)
            loaded_messages_serial = graph_input.get("messages", [])
            messages_list_obj = []
            if isinstance(loaded_messages_serial, list):
                for msg_data in loaded_messages_serial:
                    try:
                        if isinstance(msg_data, dict) and "type" in msg_data and "content" in msg_data:
                            msg_type, content, add_kwargs = msg_data.get("type"), msg_data.get("content"), msg_data.get("additional_kwargs", {})
                            if content is not None:
                                if msg_type == "human": messages_list_obj.append(HumanMessage(content=content, additional_kwargs=add_kwargs))
                                elif msg_type == "ai" or msg_type == "assistant": messages_list_obj.append(AIMessage(content=content, additional_kwargs=add_kwargs))
                                else: messages_list_obj.append(BaseMessage(type=msg_type, content=content, additional_kwargs=add_kwargs))
                        elif isinstance(msg_data, BaseMessage): messages_list_obj.append(msg_data)
                    except Exception as e_des: print(f"  [ERROR Orchestrator] Deserializing message failed: {e_des}, data: {msg_data}")
            graph_input["messages"] = messages_list_obj
            assumption_probed_last_turn = graph_input.get("assumption_being_probed_now")
            if assumption_probed_last_turn:
                current_probed_list: List[str] = graph_input.get("probed_assumptions", [])
                if assumption_probed_last_turn not in current_probed_list: current_probed_list.append(assumption_probed_last_turn)
                graph_input["probed_assumptions"] = current_probed_list
                graph_input["assumption_being_probed_now"] = None
            graph_input.setdefault("messages", []).append(HumanMessage(content=user_input))
    else:
        if not current_state_from_store : is_first_turn_of_session = True
        else: graph_input = current_state_from_store

    if is_first_turn_of_session:
        if not initial_topic:
             print("[ERROR Orchestrator] First turn but no initial_topic or user_input provided.")
             raise HTTPException(status_code=400, detail="Initial topic or user input is required for the first turn.")
        graph_input = {
            "messages": [HumanMessage(content=initial_topic)], "raw_topic": initial_topic, "raw_idea": initial_topic,
            "initial_topic": initial_topic, "has_asked_initial": False, "motivation_cleared": False,
            "final_motivation_summary": None, "idea_summary": None, "motivation_summary": None,
            "identified_assumptions": [], "probed_assumptions": [], "assumption_being_probed_now": None,
            "assumptions_fully_probed": False, "findings_summary": None, "older_history_summary": None, "error_message": None,
        }
        print(f"  [DEBUG Orchestrator] Initialized new state for session {session_id} using initial_topic: '{initial_topic}'")

    assistant_response_to_user = None
    final_state_to_save = graph_input

    try:
        print(f"  [DEBUG Orchestrator] Calling app_why_graph.ainvoke with input keys: {list(graph_input.keys())}")
        print(f"  [DEBUG Orchestrator] Value of 'has_asked_initial' in graph_input BEFORE ainvoke: {graph_input.get('has_asked_initial')}")
        print(f"  [DEBUG Orchestrator] Content of 'messages' in graph_input BEFORE ainvoke (showing last 3): {[m.content if isinstance(m, BaseMessage) else m for m in graph_input.get('messages', [])[-3:]]}")

        final_run_output = await app_why_graph.ainvoke(graph_input, config)
        print(f"  [DEBUG Orchestrator] ainvoke call completed.")
        print(f"  [DEBUG Orchestrator] Full final_run_output from ainvoke: {final_run_output}")

        if not isinstance(final_run_output, dict):
            print(f"  [ERROR Orchestrator] ainvoke returned unexpected type: {type(final_run_output)}")
            assistant_response_to_user = "(오류: 그래프 응답 형식 문제)"
        else:
            final_state_to_save = final_run_output.copy() # 중요: 복사본으로 작업
            interrupted_by_node_with_message = False
            
            # --- START: Modified Interrupt data handling (v6) ---
            interrupt_payload_list = final_state_to_save.get("__interrupt__")
            actual_interrupt_object = None
            
            if isinstance(interrupt_payload_list, list) and interrupt_payload_list:
                actual_interrupt_object = interrupt_payload_list[0]
            elif isinstance(interrupt_payload_list, (GraphInterrupt, TypesInterrupt)): # langgraph.errors 또는 langgraph.types의 Interrupt 객체
                actual_interrupt_object = interrupt_payload_list

            if actual_interrupt_object:
                print(f"    [DEBUG DataMergeAttempt] actual_interrupt_obj_for_data type: {type(actual_interrupt_object)}")
                # Interrupt 객체의 value가 노드가 전달한 상태 업데이트 딕셔너리일 것으로 기대
                interrupt_value = getattr(actual_interrupt_object, 'value', None)
                
                if isinstance(interrupt_value, dict):
                    print(f"    [DEBUG DataMerge] Found data dict in Interrupt object's value: {interrupt_value}")
                    # 노드가 전달한 상태 업데이트로 final_state_to_save를 덮어씁니다.
                    final_state_to_save.update(interrupt_value)
                    print(f"      [DEBUG DataMerge] Merged/Updated final_state_to_save with Interrupt's value (dict).")
                    # 사용자에게 전달할 메시지는 이 딕셔너리 내의 특정 키에서 가져옵니다.
                    if "user_facing_message" in interrupt_value and interrupt_value["user_facing_message"]:
                        assistant_response_to_user = str(interrupt_value["user_facing_message"])
                        interrupted_by_node_with_message = True
                        print(f"      [DEBUG DataMerge] Using 'user_facing_message' from interrupt data: '{assistant_response_to_user[:100]}...'")
                    elif "clarification_question" in interrupt_value and interrupt_value["clarification_question"]:
                        assistant_response_to_user = str(interrupt_value["clarification_question"])
                        interrupted_by_node_with_message = True
                        print(f"      [DEBUG DataMerge] Using 'clarification_question' from interrupt data: '{assistant_response_to_user[:100]}...'")
                elif interrupt_value is not None: # value가 dict가 아니고 단순 문자열 등일 경우
                    value_str = str(interrupt_value)
                    if value_str.strip():
                        assistant_response_to_user = value_str
                        interrupted_by_node_with_message = True
                        print(f"    [DEBUG RespLogic P2-DirectValue] Response from interrupt object's direct 'value': '{assistant_response_to_user[:100]}...'")
                else:
                    print(f"    [DEBUG DataMerge] Interrupt object's value is None or not a dict. Interrupt object: {actual_interrupt_object}")
            # --- END: Modified Interrupt data handling ---

            print(f"    [DEBUG StateCheck] 'has_asked_initial' in final_state_to_save AFTER DataMerge/Interrupt Handling: {final_state_to_save.get('has_asked_initial')}")
            print(f"    [DEBUG StateCheck] 'messages' in final_state_to_save AFTER DataMerge/Interrupt Handling (showing last 3): {[m.content if isinstance(m, BaseMessage) else (m.get('content') if isinstance(m,dict) else m) for m in final_state_to_save.get('messages', [])[-3:]]}")

            # P1 로직은 이제 DataMerge 이후의 final_state_to_save를 기준으로 동작
            if not interrupted_by_node_with_message: # DataMerge에서 user_facing_message 등을 못 찾은 경우
                clarification_q = final_state_to_save.get("clarification_question")
                assumption_q = final_state_to_save.get("assumption_question")
                assistant_msg_from_state = final_state_to_save.get("assistant_message")

                if clarification_q and str(clarification_q).strip():
                    assistant_response_to_user = str(clarification_q)
                    interrupted_by_node_with_message = True
                    print(f"    [DEBUG RespLogic P1-Fallback] Response from 'clarification_question': '{assistant_response_to_user[:100]}...'")
                elif assumption_q and str(assumption_q).strip():
                    assistant_response_to_user = str(assumption_q)
                    interrupted_by_node_with_message = True
                    print(f"    [DEBUG RespLogic P1-Fallback] Response from 'assumption_question': '{assistant_response_to_user[:100]}...'")
                elif assistant_msg_from_state and str(assistant_msg_from_state).strip():
                    assistant_response_to_user = str(assistant_msg_from_state)
                    interrupted_by_node_with_message = True
                    print(f"    [DEBUG RespLogic P1-Fallback] Response from 'assistant_message': '{assistant_response_to_user[:100]}...'")

            if not interrupted_by_node_with_message:
                print(f"    [DEBUG RespLogic P3] No explicit interrupt message from P1 or P2/DataMerge.")
                # ... (P3 fallback logic은 이전과 동일하게 유지) ...
                current_findings = final_state_to_save.get('findings_summary')
                if current_findings and str(current_findings).strip():
                    assistant_response_to_user = str(current_findings)
                    print(f"    [DEBUG RespLogic P3] Using 'findings_summary': '{assistant_response_to_user[:100]}...'")
                else:
                    messages_in_state = final_state_to_save.get('messages', [])
                    if messages_in_state and isinstance(messages_in_state[-1], AIMessage) and messages_in_state[-1].content.strip():
                        assistant_response_to_user = messages_in_state[-1].content
                        print(f"    [DEBUG RespLogic P3] Using last AIMessage in state: '{assistant_response_to_user[:100]}...'")
                    else:
                        assistant_response_to_user = "다음 탐색이 완료되었거나, 추가 진행을 위한 정보가 필요합니다."
                        print(f"    [DEBUG RespLogic P3] Using default completion/fallback message.")

    except HTTPException:
        raise
    except Exception as e_invoke:
        print(f"  [ERROR Orchestrator] Exception during graph execution for session {session_id}: {type(e_invoke).__name__}")
        traceback.print_exc()
        assistant_response_to_user = f"(오류: 그래프 실행 중 문제 발생 - {e_invoke})"

    # ... (상태 저장 로직 및 최종 반환 로직은 이전 답변의 v6와 동일하게 유지) ...
    if not (final_state_to_save and isinstance(final_state_to_save, dict)):
        print(f"  [WARN Orchestrator] final_state_to_save is not a valid dictionary. Attempting to use graph_input for saving.")
        final_state_to_save = graph_input if isinstance(graph_input, dict) else {}
            
    if "messages" not in final_state_to_save:
        final_state_to_save["messages"] = []

    current_messages_for_save_processing = final_state_to_save.get("messages", [])
    processed_messages_for_state = [] 
    if isinstance(current_messages_for_save_processing, list):
        for i, msg_data in enumerate(current_messages_for_save_processing):
            if isinstance(msg_data, BaseMessage):
                processed_messages_for_state.append(msg_data)
            elif isinstance(msg_data, dict) and "type" in msg_data and "content" in msg_data:
                msg_type, content, add_kwargs = msg_data.get("type"), msg_data.get("content"), msg_data.get("additional_kwargs", {})
                if content is not None:
                    if msg_type == "human": processed_messages_for_state.append(HumanMessage(content=content, additional_kwargs=add_kwargs))
                    elif msg_type == "ai" or msg_type == "assistant": processed_messages_for_state.append(AIMessage(content=content, additional_kwargs=add_kwargs))
            
        final_state_to_save["messages"] = processed_messages_for_state 
    else:
        print(f"  [WARN Orchestrator] 'messages' in final_state_to_save is not a list. Resetting to empty list for saving.")
        final_state_to_save["messages"] = []

    print(f"  [DEBUG Orchestrator] Value of 'has_asked_initial' in final_state_to_save BEFORE serialization: {final_state_to_save.get('has_asked_initial')}")
    print(f"  [DEBUG Orchestrator] Content of 'messages' in final_state_to_save BEFORE serialization (showing last 3): {[m.content if isinstance(m, BaseMessage) else (m.get('content') if isinstance(m, dict) else m) for m in final_state_to_save.get('messages', [])[-3:]]}")

    try:
        serializable_state_for_db = _serialize_state_for_db(final_state_to_save)
        if serializable_state_for_db:
            print(f"  [DEBUG Orchestrator] Value of 'has_asked_initial' in serializable_state_for_db: {serializable_state_for_db.get('has_asked_initial')}")
            await user_store.upsert(session_id, serializable_state_for_db)
            print(f"  [DEBUG Orchestrator] ✓ State saved to UserStore for session {session_id} (keys: {list(serializable_state_for_db.keys())}).")
        else:
            print(f"  [WARN Orchestrator] Serializable state for UserStore is empty. Session: {session_id}. Original final_state_to_save keys: {list(final_state_to_save.keys()) if isinstance(final_state_to_save, dict) else 'N/A'}")
    except Exception as e_upsert:
        print(f"  [ERROR Orchestrator] Failed to upsert final state to UserStore: {e_upsert}")
        traceback.print_exc()
        if not assistant_response_to_user or assistant_response_to_user.startswith("다음 탐색이 완료되었거나"):
             assistant_response_to_user = "(오류: 대화 상태 저장에 실패했습니다. 다음 대화에 영향이 있을 수 있습니다.)"

    if not (assistant_response_to_user and str(assistant_response_to_user).strip()):
         print(f"  [WARN Orchestrator] Final assistant_response_to_user is empty or None. Setting default. Was: '{assistant_response_to_user}'")
         assistant_response_to_user = "요청이 처리되었으나 반환할 특정 메시지가 없습니다."

    print(f"[DEBUG Orchestrator] --- Ending Turn --- Session: {session_id} --- Returning: '{str(assistant_response_to_user)[:100]}...'")
    return str(assistant_response_to_user)

