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
# print("[Orchestrator Setup] Using MemorySaver for LangGraph's internal checkpointing.")
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
            # print(f"  [COND_EDGE] decide_after_motivation: motivation_cleared={motivation_cleared}")
            if motivation_cleared: # 노드가 명확하다고 판단하여 상태를 반환한 경우
                return "summarize_idea_motivation"
            # 노드가 interrupt를 발생시켰거나, 명확하지 않다고 판단하여 특정 키 없이 상태를 반환한 경우
            # (현재 motivation_elicitation_node는 명확하지 않으면 항상 interrupt 발생)
            # print(f"  [COND_EDGE][WARN] decide_after_motivation: motivation not cleared or node interrupted, ending graph run for this turn.")
            return END # 현재 턴 종료, 오케스트레이터가 interrupt 처리

        def decide_after_summary(state: WhyGraphState) -> str:
            idea_summary_exists = bool(state.get("idea_summary", "").strip())
            motivation_summary_exists = bool(state.get("motivation_summary", "").strip()) or bool(state.get("final_motivation_summary", "").strip())
            # print(f"  [COND_EDGE] decide_after_summary: idea_summary_exists={idea_summary_exists}, motivation_summary_exists={motivation_summary_exists}")
            if idea_summary_exists and motivation_summary_exists:
                 return "identify_assumptions"
            # print(f"  [COND_EDGE][WARN] decide_after_summary: Missing summary, ending.")
            return END

        def decide_after_identification(state: WhyGraphState) -> str:
            assumptions_identified = bool(state.get("identified_assumptions"))
            # print(f"  [COND_EDGE] decide_after_identification: assumptions_identified={assumptions_identified}")
            if assumptions_identified:
                return "probe_assumption"
            return "findings_summarization"

        def decide_after_probing(state: WhyGraphState) -> str:
            assumptions_fully_probed = state.get("assumptions_fully_probed", False)
            current_assumption = state.get("assumption_being_probed_now")
            probed_assumptions = state.get("probed_assumptions", [])
            identified_assumptions = state.get("identified_assumptions", [])
            
            # 현재 가정이 있고, 아직 완전히 탐구되지 않았다면 계속 탐구
            if current_assumption and current_assumption not in probed_assumptions:
                return "probe_assumption"
            
            # 모든 가정이 탐구되었다면 findings_summarization으로 이동
            if assumptions_fully_probed or len(probed_assumptions) >= len(identified_assumptions):
                return "findings_summarization"
            
            # 다음 가정으로 이동
            return "probe_assumption"

        def decide_after_findings(state: WhyGraphState) -> str:
            findings_summary_exists = bool(state.get("findings_summary", "").strip())
            # print(f"  [COND_EDGE] decide_after_findings: findings_summary_exists={findings_summary_exists}")
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
        # print("[Orchestrator Setup] Graph compiled successfully.")
    except Exception as e_compile:
        # print(f"[Orchestrator Setup][ERROR] Failed to compile graph: {e_compile}")
        traceback.print_exc()
        app_why_graph = None
else:
    # print("[Orchestrator Setup][ERROR] Cannot compile graph: Checkpointer is None.")
    pass


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
    if not app_why_graph:
         raise HTTPException(status_code=500, detail="Graph is not compiled or unavailable.")

    config: RunnableConfig = {"configurable": {"thread_id": session_id}}
    graph_input: Dict[str, Any] = {}

    is_first_turn_of_session = False
    current_state_from_store = await user_store.load(session_id) or {}

    if user_input is not None:
        if not current_state_from_store:
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
                    except Exception as e_des: pass
            graph_input["messages"] = messages_list_obj
            
            # 사용자 입력이 마지막 메시지와 동일하면 추가하지 않음
            if graph_input.get("messages") and isinstance(graph_input["messages"][-1], HumanMessage):
                if graph_input["messages"][-1].content == user_input:
                    pass  # 이미 추가된 입력이면 무시
                else:
                    graph_input["messages"].append(HumanMessage(content=user_input))
            else:
                graph_input.setdefault("messages", []).append(HumanMessage(content=user_input))
    else:
        if not current_state_from_store : is_first_turn_of_session = True
        else: graph_input = current_state_from_store

    if is_first_turn_of_session:
        if not initial_topic:
             raise HTTPException(status_code=400, detail="Initial topic or user input is required for the first turn.")
        graph_input = {
            "messages": [HumanMessage(content=initial_topic)], "raw_topic": initial_topic, "raw_idea": initial_topic,
            "initial_topic": initial_topic, "has_asked_initial": False, "motivation_cleared": False,
            "final_motivation_summary": None, "idea_summary": None, "motivation_summary": None,
            "identified_assumptions": [], "probed_assumptions": [], "assumption_being_probed_now": None,
            "assumptions_fully_probed": False, "findings_summary": None, "older_history_summary": None, "error_message": None,
            "probe_messages": [], "current_node": "motivation_elicitation"
        }

    assistant_response_to_user = None
    final_state_to_save = graph_input

    try:
        final_run_output = await app_why_graph.ainvoke(graph_input, config)

        if not isinstance(final_run_output, dict):
            assistant_response_to_user = "(오류: 그래프 응답 형식 문제)"
        else:
            final_state_to_save = final_run_output.copy()
            interrupted_by_node_with_message = False
            
            interrupt_payload_list = final_state_to_save.get("__interrupt__")
            actual_interrupt_object = None
            
            if isinstance(interrupt_payload_list, list) and interrupt_payload_list:
                actual_interrupt_object = interrupt_payload_list[0]
            elif isinstance(interrupt_payload_list, (GraphInterrupt, TypesInterrupt)):
                actual_interrupt_object = interrupt_payload_list

            if actual_interrupt_object:
                interrupt_value = getattr(actual_interrupt_object, 'value', None)
                
                if isinstance(interrupt_value, dict):
                    final_state_to_save.update(interrupt_value)
                    if "user_facing_message" in interrupt_value and interrupt_value["user_facing_message"]:
                        assistant_response_to_user = str(interrupt_value["user_facing_message"])
                        interrupted_by_node_with_message = True
                    elif "clarification_question" in interrupt_value and interrupt_value["clarification_question"]:
                        assistant_response_to_user = str(interrupt_value["clarification_question"])
                        interrupted_by_node_with_message = True
                elif interrupt_value is not None:
                    value_str = str(interrupt_value)
                    if value_str.strip():
                        assistant_response_to_user = value_str
                        interrupted_by_node_with_message = True

            if not interrupted_by_node_with_message:
                clarification_q = final_state_to_save.get("clarification_question")
                assumption_q = final_state_to_save.get("assumption_question")
                assistant_msg_from_state = final_state_to_save.get("assistant_message")

                if clarification_q and str(clarification_q).strip():
                    assistant_response_to_user = str(clarification_q)
                    interrupted_by_node_with_message = True
                elif assumption_q and str(assumption_q).strip():
                    assistant_response_to_user = str(assumption_q)
                    interrupted_by_node_with_message = True
                elif assistant_msg_from_state and str(assistant_msg_from_state).strip():
                    assistant_response_to_user = str(assistant_msg_from_state)
                    interrupted_by_node_with_message = True

            if not interrupted_by_node_with_message:
                current_findings = final_state_to_save.get('findings_summary')
                if current_findings and str(current_findings).strip():
                    assistant_response_to_user = str(current_findings)
                else:
                    messages_in_state = final_state_to_save.get('messages', [])
                    if messages_in_state and isinstance(messages_in_state[-1], AIMessage) and messages_in_state[-1].content.strip():
                        assistant_response_to_user = messages_in_state[-1].content
                    else:
                        assistant_response_to_user = "다음 탐색이 완료되었거나, 추가 진행을 위한 정보가 필요합니다."

    except HTTPException:
        raise
    except Exception as e_invoke:
        traceback.print_exc()
        assistant_response_to_user = f"(오류: 그래프 실행 중 문제 발생 - {e_invoke})"

    if not (final_state_to_save and isinstance(final_state_to_save, dict)):
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
        final_state_to_save["messages"] = []

    try:
        serializable_state_for_db = _serialize_state_for_db(final_state_to_save)
        if serializable_state_for_db:
            await user_store.upsert(session_id, serializable_state_for_db)
    except Exception as e_upsert:
        traceback.print_exc()
        if not assistant_response_to_user or assistant_response_to_user.startswith("다음 탐색이 완료되었거나"):
             assistant_response_to_user = "(오류: 대화 상태 저장에 실패했습니다. 다음 대화에 영향이 있을 수 있습니다.)"

    if not (assistant_response_to_user and str(assistant_response_to_user).strip()):
         assistant_response_to_user = "요청이 처리되었으나 반환할 특정 메시지가 없습니다."

    return str(assistant_response_to_user)

