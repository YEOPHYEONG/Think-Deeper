# backend/app/core/checkpointers.py
import pickle
import asyncio
import uuid # Ensure uuid is imported
from typing import NamedTuple, Optional, Dict, Any, AsyncIterator, Union, List, TypedDict
from datetime import datetime, timezone
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from .sql_checkpointer import SQLCheckpointer
from .redis_checkpointer import RedisCheckpointer

# ===== LangGraph Checkpoint TypedDict Structure (Assumption) =====
# Verify against your installed LangGraph version's source code!
class Checkpoint(TypedDict, total=False):
    """Assumed structure for LangGraph's internal Checkpoint object"""
    id: Optional[str] # ID should be a string, not None, when accessed by LangGraph
    v: int
    ts: str
    channel_values: Dict[str, Any]
    channel_versions: Dict[str, Any]
    versions_seen: Dict[str, Dict[str, Any]]
    pending_sends: Optional[List[Any]] 

# ===== LangGraph CheckpointTuple Structure (Assumption) =====
# Verify against your installed LangGraph version's source code!
class CheckpointTuple(NamedTuple):
    """Assumed structure for LangGraph's CheckpointTuple"""
    config: RunnableConfig
    checkpoint: Checkpoint # Type hint using the Checkpoint TypedDict
    metadata: Optional[Dict[str, Any]] = None
    parent_config: Optional[RunnableConfig] = None
    pending_writes: Optional[Any] = None
    pending_sends: Optional[Any] = None


class CombinedCheckpointer:
    def __init__(self, redis_cp: RedisCheckpointer, sql_cp: SQLCheckpointer):
        self.redis_cp = redis_cp
        self.sql_cp = sql_cp

    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        """Loads state (wrapper) from Redis -> SQL and returns a dict
           containing keys expected by LangGraph (channel_values, metadata, etc.)."""
        runnable_config: RunnableConfig = config
        wrapper = await self.redis_cp.aget(runnable_config)
        print("[CHECKPOINTER] Redis 조회 결과:", wrapper) 
        if wrapper is None:
            wrapper = await self.sql_cp.aget(runnable_config)
            print("[CHECKPOINTER] SQL 조회 결과:", wrapper) 

        if wrapper is None:
            # Default structure if nothing found
            wrapper = {
                "channel_values": {"__default__": []}, # Ensure channel_values is a dict
                "metadata": {"step": 0}, 
                "versions_seen": {},
                "channel_versions": {},
            }
            print("[CHECKPOINTER] 빈 상태, 기본 wrapper 반환:", wrapper) 
        else:
            # Ensure essential keys and structure in the loaded wrapper
            cv = wrapper.get("channel_values")
            if not isinstance(cv, dict): # Ensure channel_values is a dict
                cv = {}
            cv.setdefault("__default__", []) # Ensure __default__ channel exists
            wrapper["channel_values"] = cv
            
            vs = wrapper.get("versions_seen", {})
            if not isinstance(vs, dict): vs = {}
            wrapper["versions_seen"] = vs
            
            cvs = wrapper.get("channel_versions", {})
            if not isinstance(cvs, dict): cvs = {}
            wrapper["channel_versions"] = cvs
            
            md = wrapper.get("metadata", {})
            if not isinstance(md, dict): md = {}
            md.setdefault("step", 0) 
            wrapper["metadata"] = md
            print("[CHECKPOINTER] wrapper 보정 후:", wrapper) 

        return {
            "channel_values":   wrapper.get("channel_values"),
            "metadata":         wrapper.get("metadata"),
            "versions_seen":    wrapper.get("versions_seen"),
            "channel_versions": wrapper.get("channel_versions"),
        }

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Loads state using aget and converts it into the CheckpointTuple format expected by LangGraph."""
        runnable_config: RunnableConfig = config
        wrapper = await self.aget(runnable_config) 

        print("\n" + "="*20 + " DEBUG inside aget_tuple " + "="*20)
        print(f"[DEBUG aget_tuple] Loaded wrapper keys from aget: {list(wrapper.keys()) if wrapper else 'None'}")
        print(f"[DEBUG aget_tuple] Config received: {runnable_config}")
        
        if wrapper is None: # Should not happen if aget returns default structure
             print("[ERROR aget_tuple] Wrapper is None, cannot proceed.")
             return None

        print(f"[DEBUG aget_tuple] Metadata from wrapper: {wrapper.get('metadata')}")

        try:
            checkpoint_id_from_config = runnable_config.get("configurable", {}).get("checkpoint_id")
            final_checkpoint_id = checkpoint_id_from_config if checkpoint_id_from_config is not None else str(uuid.uuid4())
            print(f"[DEBUG aget_tuple] Checkpoint ID from config: {checkpoint_id_from_config}")
            print(f"[DEBUG aget_tuple] Final Checkpoint ID for Checkpoint object: {final_checkpoint_id}")

            checkpoint_content: Checkpoint = {
                "id": final_checkpoint_id,
                "v": 1, # Or derive appropriately
                "ts": datetime.now(timezone.utc).isoformat(),
                "channel_values": wrapper.get("channel_values", {}), # Ensure this is a dict
                "channel_versions": wrapper.get("channel_versions", {}),
                "versions_seen": wrapper.get("versions_seen", {}),
                "pending_sends": [], 
            }
            print(f"[DEBUG aget_tuple] Constructed Checkpoint object for tuple: {checkpoint_content}")

            metadata_content = wrapper.get("metadata", {})
            metadata_content.setdefault("step", 0)
            print(f"[DEBUG aget_tuple] Metadata object for tuple: {metadata_content}")

            tuple_to_return = CheckpointTuple(
                config=runnable_config,
                checkpoint=checkpoint_content, 
                metadata=metadata_content,    
                parent_config=None,            
                pending_writes=None,           
                pending_sends=None,            
            )

            print(f"[DEBUG aget_tuple] Returning CheckpointTuple type: {type(tuple_to_return)}")
            print(f"[DEBUG aget_tuple] Returning CheckpointTuple content (showing keys): { {field: getattr(tuple_to_return, field, 'N/A') for field in CheckpointTuple._fields} }")
            print(f"[DEBUG aget_tuple] Metadata field in tuple: {tuple_to_return.metadata}")
            print(f"[DEBUG aget_tuple] Checkpoint field type in tuple: {type(tuple_to_return.checkpoint)}")
            print(f"[DEBUG aget_tuple] Checkpoint field keys in tuple: {list(tuple_to_return.checkpoint.keys()) if isinstance(tuple_to_return.checkpoint, dict) else 'N/A'}") 

        except Exception as e:
            print(f"[ERROR aget_tuple] Failed to create CheckpointTuple: {e}")
            import traceback
            traceback.print_exc() 
            tuple_to_return = None

        print("="*20 + " END DEBUG inside aget_tuple " + "="*20 + "\n")
        return tuple_to_return

    async def aput(self, config: Dict[str, Any],
                   checkpoint: Dict[str, Any], # This is the full Checkpoint object from LangGraph
                   metadata: Dict[str, Any], # This is the metadata from the CheckpointTuple
                   channel_versions_arg: Any # This is checkpoint.get("channel_versions")
                  ):
        runnable_config: RunnableConfig = config
        print("[CHECKPOINTER] aput 호출됨") 
        print("  - config:", runnable_config)
        print("  - checkpoint (full object from LangGraph) keys:", list(checkpoint.keys()))
        print("  - metadata (from CheckpointTuple.metadata, should be graph metadata):", metadata)
        print("  - channel_versions_arg (likely checkpoint['channel_versions']):", channel_versions_arg)

        # Process metadata, ensure 'step' exists
        if not isinstance(metadata, dict):
             metadata_to_save = {"step": 0} # Default if metadata is not a dict
        else:
             metadata_to_save = metadata.copy() # Use the graph metadata
             # 'step' should be managed by LangGraph and present in 'metadata'
             metadata_to_save.setdefault("step", metadata.get("step", 0))


        print(f"  - metadata to save (this is graph metadata): {metadata_to_save}")

        # Structure to save (wrapper format for aget)
        # Extract application state and relevant checkpoint info correctly
        state_to_store = {
            "channel_values": checkpoint.get("channel_values", {}), # Actual application state
            "metadata": metadata_to_save, # Graph-level metadata
            "channel_versions": checkpoint.get("channel_versions", {}), # From the main checkpoint object
            "versions_seen": checkpoint.get("versions_seen", {}), # From the main checkpoint object
            # We might also want to store 'v', 'ts', 'id' of the checkpoint if needed for retrieval logic,
            # but typically aget/aget_tuple reconstructs a new CheckpointTuple.
            # For now, this matches what aget expects to load for channel_values, metadata, etc.
        }
        print("  - state_to_store (what is actually saved) keys:", list(state_to_store.keys()))
        print(f"  - state_to_store['channel_values'] sample: {str(state_to_store['channel_values'])[:200]}...")


        # Save to Redis and SQL
        await self.redis_cp.aset(runnable_config, state_to_store)
        await self.sql_cp.aset(runnable_config, state_to_store)

    async def aput_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None: return None
    async def adelete(self, config: Dict[str, Any]) -> None:
        runnable_config: RunnableConfig = config
        await self.redis_cp.adelete(runnable_config)
        await self.sql_cp.adelete(runnable_config)
    async def adelete_thread(self, config: Dict[str, Any]) -> None: return await self.adelete(config)
    
    async def alist(self, config: Dict[str, Any], *, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        # Added before and limit for compatibility with some LangGraph versions if they expect it
        # Basic implementation: yields the current checkpoint if it exists
        runnable_config: RunnableConfig = config
        tup = await self.aget_tuple(runnable_config)
        if tup: 
            yield tup
            
    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        runnable_config: RunnableConfig = config
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aget(runnable_config))
    
    def put(self, config: Dict[str, Any], checkpoint_obj_from_lg: dict, metadata_from_lg: dict, channel_versions_from_lg: dict) -> None:
        # This synchronous 'put' might be called by some LangGraph internal mechanisms
        # It should align with how 'aput' works.
        runnable_config: RunnableConfig = config
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        # The arguments here match the async aput
        loop.run_until_complete(self.aput(runnable_config, checkpoint_obj_from_lg, metadata_from_lg, channel_versions_from_lg))

    def put_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None:
        runnable_config: RunnableConfig = config
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.aput_writes(runnable_config, writes, task_id, task_path))
    
    def delete_thread(self, thread_id: str) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        runnable_config: RunnableConfig = config
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.adelete_thread(runnable_config))
    
    # list is the synchronous version of alist
    def list(self, config: Dict[str, Any], *, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> List[CheckpointTuple]:
        runnable_config: RunnableConfig = config
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        
        async def _collect_alist():
            results = []
            async for item in self.alist(runnable_config, before=before, limit=limit):
                results.append(item)
            return results
        return loop.run_until_complete(_collect_alist())

    def get_next_version(self, current_version: Optional[int], channel_state: Any) -> int: 
        return (current_version or 0) + 1
        
    async def aget_user_visible_messages(self, config: Dict[str, Any]) -> Optional[List[Union[BaseMessage, dict]]]:
        runnable_config: RunnableConfig = config
        # aget returns the wrapper with 'channel_values' containing the app state
        wrapper = await self.aget(runnable_config)
        if not wrapper or not wrapper.get("channel_values"): 
            return None # No state or no channel_values in state
        
        app_state = wrapper["channel_values"] # This should be the dict of application state
        
        # Try to get messages from 'messages' key first, then from '__default__'
        messages = app_state.get("messages")
        if messages is None:
            # If 'messages' key doesn't exist, try '__default__' from channel_values
            # This part might be redundant if 'messages' is the sole source of truth
            # For now, keeping similar logic to original if app_state can be directly channel_values
            if isinstance(app_state, dict): # Ensure app_state is a dict
                 messages = app_state.get("__default__", []) 
            else: # Should not happen if aget works correctly
                 messages = []
        
        # Ensure messages is a list
        if not isinstance(messages, list):
            return [] # Return empty list if messages is not a list

        # Deserialize if messages are in dict format (e.g., from JSON)
        # This step might be needed if SQLCheckpointer returns serialized messages
        deserialized_messages = []
        for msg_data in messages:
            if isinstance(msg_data, dict) and "type" in msg_data and "content" in msg_data:
                if msg_data["type"] == "human":
                    deserialized_messages.append(HumanMessage(content=msg_data["content"], additional_kwargs=msg_data.get("additional_kwargs", {})))
                elif msg_data["type"] == "ai":
                    deserialized_messages.append(AIMessage(content=msg_data["content"], additional_kwargs=msg_data.get("additional_kwargs", {})))
                else: # Could be SystemMessage or other types, or already BaseMessage objects
                    deserialized_messages.append(msg_data) 
            elif isinstance(msg_data, BaseMessage): # Already a BaseMessage object
                deserialized_messages.append(msg_data)
            # else: skip if format is unknown
        return deserialized_messages

