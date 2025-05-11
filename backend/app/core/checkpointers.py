# backend/app/core/checkpointers.py
import pickle
import asyncio
import uuid # Ensure uuid is imported
from typing import NamedTuple, Optional, Dict, Any, AsyncIterator, Union, List, TypedDict, Tuple # Import Tuple
from datetime import datetime, timezone
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Added HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

# Assuming SQLCheckpointer and RedisCheckpointer are correctly defined elsewhere
from .sql_checkpointer import SQLCheckpointer
from .redis_checkpointer import RedisCheckpointer

# ===== LangGraph Checkpoint TypedDict Structure (Assumption) =====
# Verify against your installed LangGraph version's source code!
class Checkpoint(TypedDict, total=False):
    """Assumed structure for LangGraph's internal Checkpoint object"""
    id: str # Changed Optional[str] to str, assuming LangGraph expects a string ID
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
    """
    A checkpointer that combines Redis (for caching/speed) and SQL (for persistence).
    Attempts to implement the LangGraph CheckpointSaver interface.
    NOTE: Conformance to the exact interface of your LangGraph version is crucial.
    """
    def __init__(self, redis_cp: RedisCheckpointer, sql_cp: SQLCheckpointer):
        self.redis_cp = redis_cp
        self.sql_cp = sql_cp
        # Indicate that this checkpointer supports saving/loading metadata
        self.is_persistent = True

    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        """Loads state (wrapper) from Redis -> SQL and returns a dict
           containing keys expected by LangGraph (channel_values, metadata, etc.)."""
        runnable_config: RunnableConfig = config
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][aget] Attempting to load state for thread_id: {thread_id}")

        wrapper = await self.redis_cp.aget(config) # Pass the full config
        print(f"[CHECKPOINTER][aget] Redis lookup result for {thread_id}: {'Found' if wrapper else 'None'}")
        if wrapper is None:
            wrapper = await self.sql_cp.aget(config) # Pass the full config
            print(f"[CHECKPOINTER][aget] SQL lookup result for {thread_id}: {'Found' if wrapper else 'None'}")
            if wrapper:
                 # If loaded from SQL, potentially cache it back to Redis
                 # Consider adding TTL logic here if caching back
                 print(f"[CHECKPOINTER][aget] Caching state from SQL to Redis for {thread_id}")
                 await self.redis_cp.aset(config, wrapper)


        if wrapper is None:
            # Default structure if nothing found ANYWHERE
            wrapper = {
                "channel_values": {"__default__": []},
                "messages": [],
                "metadata": {"step": -1}, # Use -1 to indicate it's a truly new state
                "versions_seen": {},
                "channel_versions": {},
            }
            print(f"[CHECKPOINTER][aget] No state found for {thread_id}, returning default wrapper.")
        else:
            # Ensure essential keys and structure in the loaded wrapper
            cv = wrapper.get("channel_values")
            if not isinstance(cv, dict): cv = {}
            cv.setdefault("__default__", [])
            wrapper["channel_values"] = cv

            if "messages" not in wrapper or not isinstance(wrapper.get("messages"), list):
                 channel_values_inner = wrapper.get("channel_values", {})
                 default_channel_state = channel_values_inner.get("__default__", {})
                 if isinstance(default_channel_state, dict):
                     wrapper["messages"] = default_channel_state.get("messages", [])
                 elif isinstance(default_channel_state, list):
                     wrapper["messages"] = default_channel_state
                 else:
                     wrapper["messages"] = []

            vs = wrapper.get("versions_seen", {})
            if not isinstance(vs, dict): vs = {}
            wrapper["versions_seen"] = vs

            cvs = wrapper.get("channel_versions", {})
            if not isinstance(cvs, dict): cvs = {}
            wrapper["channel_versions"] = cvs

            md = wrapper.get("metadata", {})
            if not isinstance(md, dict): md = {}
            md.setdefault("step", 0) # Default step to 0 if loaded state has no step
            wrapper["metadata"] = md
            print(f"[CHECKPOINTER][aget] Loaded state for {thread_id}, processed wrapper.")

        return wrapper


    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Loads state using aget and converts it into the CheckpointTuple format expected by LangGraph."""
        runnable_config: RunnableConfig = config
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][aget_tuple] Loading state for thread_id: {thread_id}")
        wrapper = await self.aget(config) # aget now returns the full wrapper

        # aget should always return a dict now
        if wrapper is None:
             print(f"[CHECKPOINTER][aget_tuple][ERROR] aget returned None unexpectedly for {thread_id}.")
             return None

        print(f"  [CHECKPOINTER][aget_tuple] Loaded wrapper keys: {list(wrapper.keys())}")
        print(f"  [CHECKPOINTER][aget_tuple] Config received: {runnable_config}")
        print(f"  [CHECKPOINTER][aget_tuple] Metadata from wrapper: {wrapper.get('metadata')}")

        try:
            # Determine checkpoint ID
            checkpoint_id_from_config = runnable_config.get("configurable", {}).get("checkpoint_id")
            # LangGraph might store the actual checkpoint ID within the metadata it saves
            checkpoint_id_from_meta = wrapper.get("metadata", {}).get("checkpoint_id")
            final_checkpoint_id = checkpoint_id_from_config or checkpoint_id_from_meta

            # --- FIX: Ensure final_checkpoint_id is always a string ---
            if final_checkpoint_id is None:
                 print(f"  [CHECKPOINTER][aget_tuple] No checkpoint ID found for new thread {thread_id}. Generating new UUID.")
                 final_checkpoint_id = str(uuid.uuid4()) # Generate a new UUID for the initial checkpoint
            # --- END FIX ---

            print(f"  [CHECKPOINTER][aget_tuple] Using Checkpoint ID: {final_checkpoint_id}")

            # Ensure channel_values is a dict
            channel_values_for_checkpoint = wrapper.get("channel_values", {})
            if not isinstance(channel_values_for_checkpoint, dict):
                channel_values_for_checkpoint = {}

            # Construct the Checkpoint object based on loaded state
            checkpoint_content: Checkpoint = {
                "v": 1, # Version 1 for the structure itself
                "id": final_checkpoint_id, # Checkpoint ID (now guaranteed to be a string)
                "ts": wrapper.get("metadata", {}).get("ts", datetime.now(timezone.utc).isoformat()), # Timestamp from metadata or now
                "channel_values": channel_values_for_checkpoint,
                "channel_versions": wrapper.get("channel_versions", {}),
                "versions_seen": wrapper.get("versions_seen", {}),
                "pending_sends": [], # Typically empty when loading
            }
            # print(f"  [CHECKPOINTER][aget_tuple] Constructed Checkpoint object: {checkpoint_content}") # Can be verbose

            metadata_content = wrapper.get("metadata", {})
            # Use step -1 for brand new threads as loaded by aget's default
            metadata_content.setdefault("step", -1 if wrapper.get("metadata", {}).get("step") == -1 else 0)
            print(f"  [CHECKPOINTER][aget_tuple] Metadata object for tuple: {metadata_content}")

            tuple_to_return = CheckpointTuple(
                config=runnable_config,
                checkpoint=checkpoint_content,
                metadata=metadata_content, # This should be the graph's metadata
                parent_config=None, # Usually None when loading directly
                pending_writes=None, # Usually None when loading directly
                pending_sends=None, # Usually None when loading directly
            )

            print(f"  [CHECKPOINTER][aget_tuple] Returning CheckpointTuple for {thread_id}.")

        except Exception as e:
            print(f"[CHECKPOINTER][aget_tuple][ERROR] Failed to create CheckpointTuple for {thread_id}: {e}")
            import traceback
            traceback.print_exc()
            tuple_to_return = None

        return tuple_to_return

    # --- FIX: Add new_versions parameter to match LangGraph call ---
    async def aput(self, config: Dict[str, Any],
                   checkpoint: Dict[str, Any],
                   metadata: Dict[str, Any],
                   new_versions: Optional[Dict[str, Union[int, str]]] = None # Added new_versions
                  ) -> RunnableConfig:
    # --- END FIX ---
        """Saves the checkpoint and metadata."""
        runnable_config: RunnableConfig = config
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = checkpoint.get("id") # ID should be present now
        if not checkpoint_id:
             print(f"[CHECKPOINTER][aput][ERROR] Checkpoint ID is missing in checkpoint object for thread {thread_id}!")
             checkpoint_id = str(uuid.uuid4()) # Assign new ID as fallback
             checkpoint["id"] = checkpoint_id

        print(f"[CHECKPOINTER][aput] Saving checkpoint for thread_id: {thread_id}, checkpoint_id: {checkpoint_id}")
        print(f"  - Config: {runnable_config}")
        # Log new_versions if needed
        print(f"  - New versions received by aput: {new_versions}") # Log the received versions

        # Metadata to save alongside the state
        if not isinstance(metadata, dict):
             metadata_to_save = {"step": 0}
        else:
             metadata_to_save = metadata.copy()
             metadata_to_save.setdefault("step", metadata.get("step", 0))
             metadata_to_save["checkpoint_id"] = checkpoint_id
             metadata_to_save["ts"] = checkpoint.get("ts")

        print(f"  - Metadata being saved: {metadata_to_save}")

        # Structure to save (wrapper format for aget)
        app_state_from_checkpoint = checkpoint.get("channel_values", {})

        # Extract 'messages' if it's a key within the app state
        messages_to_store = []
        if isinstance(app_state_from_checkpoint, dict):
            messages_candidate = app_state_from_checkpoint.get("messages")
            if isinstance(messages_candidate, list):
                messages_to_store = messages_candidate
            else:
                default_channel_state = app_state_from_checkpoint.get("__default__", {})
                if isinstance(default_channel_state, dict):
                    messages_candidate_default = default_channel_state.get("messages")
                    if isinstance(messages_candidate_default, list):
                         messages_to_store = messages_candidate_default

        state_to_store = {
            "channel_values": app_state_from_checkpoint,
            "messages": messages_to_store,
            "metadata": metadata_to_save,
            # Use versions from the checkpoint object itself, as it should be the source of truth
            "channel_versions": checkpoint.get("channel_versions", {}),
            "versions_seen": checkpoint.get("versions_seen", {}),
        }

        # Save to Redis and SQL
        await self.redis_cp.aset(runnable_config, state_to_store)
        await self.sql_cp.aset(runnable_config, state_to_store)

        print(f"[CHECKPOINTER][aput] Saved checkpoint {checkpoint_id} for thread {thread_id}.")
        # Return the config, ensuring it includes the checkpoint_id used for saving
        saved_config = runnable_config.copy()
        if "configurable" not in saved_config: saved_config["configurable"] = {}
        saved_config["configurable"]["checkpoint_id"] = checkpoint_id
        return saved_config


    async def aput_writes(self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str) -> RunnableConfig:
        """Applies partial writes to the current state and saves."""
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][aput_writes] Applying writes for thread {thread_id}, task {task_id}")
        print(f"  - Writes: {writes}")

        current_tuple = await self.aget_tuple(config)
        if not current_tuple:
            print(f"[CHECKPOINTER][aput_writes][ERROR] Cannot apply writes, failed to load current state for {thread_id}")
            return config

        updated_checkpoint = current_tuple.checkpoint.copy()
        if "channel_values" not in updated_checkpoint: updated_checkpoint["channel_values"] = {}

        # --- Simplified write application (overwrite) ---
        for channel, value in writes:
            updated_checkpoint["channel_values"][channel] = value
        # --- End Simplified write application ---

        updated_checkpoint["ts"] = datetime.now(timezone.utc).isoformat()

        print(f"  - State after applying writes (before save): {updated_checkpoint['channel_values']}")

        # Save the updated state using aput
        # We need to pass the expected number of arguments to aput now
        # The 'new_versions' for aput_writes might need calculation based on 'writes'
        # For simplicity, passing None, assuming aput primarily uses checkpoint object's versions
        saved_config = await self.aput(config, updated_checkpoint, current_tuple.metadata, new_versions=None)
        print(f"[CHECKPOINTER][aput_writes] Finished applying writes for thread {thread_id}, task {task_id}")
        return saved_config

    async def adelete(self, config: Dict[str, Any]) -> None:
        """Deletes a specific checkpoint or potentially the latest one."""
        runnable_config: RunnableConfig = config
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        print(f"[CHECKPOINTER][adelete] Deleting checkpoint for thread_id: {thread_id}, checkpoint_id: {checkpoint_id or 'latest'}")
        await self.redis_cp.adelete(config)
        await self.sql_cp.adelete(config)
        print(f"[CHECKPOINTER][adelete] Deletion complete for {thread_id}, {checkpoint_id or 'latest'}")


    async def adelete_thread(self, config: Dict[str, Any]) -> None:
        """Deletes all checkpoints associated with a thread."""
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][adelete_thread] Deleting ALL checkpoints for thread_id: {thread_id}")
        # Assuming Redis/SQL checkpointers have methods to delete by thread_id prefix/query
        await self.redis_cp.adelete_thread(config)
        await self.sql_cp.adelete_thread(config)
        print(f"[CHECKPOINTER][adelete_thread] Deletion complete for thread {thread_id}.")


    async def alist(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        """ Lists checkpoints for a thread, potentially filtered. """
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][alist] Listing checkpoints for thread_id: {thread_id}, filter: {filter}, before: {before}, limit: {limit}")

        # Delegate to SQL checkpointer assuming it handles listing and filtering
        if hasattr(self.sql_cp, 'alist') and asyncio.iscoroutinefunction(self.sql_cp.alist):
            async for tup in self.sql_cp.alist(config, filter=filter, before=before, limit=limit):
                yield tup
        else:
            print("[CHECKPOINTER][alist][WARN] SQL checkpointer does not have an async 'alist' method. Cannot list history.")
            # If listing isn't supported or nothing found, the loop will finish,
            # and an empty async iterator will be returned implicitly.


    # --- Synchronous Methods ---

    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        """Synchronous version of aget."""
        print(f"[CHECKPOINTER][SYNC] get 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aget(config))

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Synchronous version of aget_tuple."""
        print(f"[CHECKPOINTER][SYNC] get_tuple 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aget_tuple(config))


    # --- FIX: Add new_versions parameter to match LangGraph call ---
    def put(self, config: Dict[str, Any],
            checkpoint: dict,
            metadata: dict,
            new_versions: Optional[Dict[str, Union[int, str]]] = None # Added new_versions
           ) -> RunnableConfig:
    # --- END FIX ---
        """Synchronous version of aput."""
        print(f"[CHECKPOINTER][SYNC] put 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        # Pass the new_versions argument to the async version
        return loop.run_until_complete(self.aput(config, checkpoint, metadata, new_versions))

    def put_writes(self, config: Dict[str, Any], writes: List[Tuple[str, Any]], task_id: str) -> RunnableConfig:
        """Synchronous version of aput_writes."""
        print(f"[CHECKPOINTER][SYNC] put_writes 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aput_writes(config, writes, task_id))

    def delete_thread(self, config: Dict[str, Any]) -> None:
        """Synchronous version of adelete_thread."""
        print(f"[CHECKPOINTER][SYNC] delete_thread 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.adelete_thread(config))

    def list(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> List[CheckpointTuple]:
        """Synchronous version of alist."""
        print(f"[CHECKPOINTER][SYNC] list 호출됨 for config: {config}")
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)

        async def _collect_alist():
            results = []
            async for item in self.alist(config, filter=filter, before=before, limit=limit):
                results.append(item)
            return results
        return loop.run_until_complete(_collect_alist())

    # --- get_next_version Method ---
    def get_next_version(self, current_version: Optional[Union[int, str]], channel_state: Any) -> Union[int, str]:
        """
        Calculates the next version for a channel based on the current version.
        LangGraph uses this for managing channel updates. A simple increment is common.
        """
        print(f"[CHECKPOINTER] get_next_version called. current_version={current_version}, type={type(current_version)}")
        if isinstance(current_version, int):
            return current_version + 1
        elif current_version is None:
            return 1 # Start with version 1
        else:
            # Handle non-integer versions if necessary, default to 1 or raise error
            try:
                return int(current_version) + 1
            except (ValueError, TypeError):
                print(f"[CHECKPOINTER][WARN] get_next_version received non-integer/None version: {current_version}. Returning 1.")
                return 1


    # --- Helper for retrieving messages ---
    async def aget_user_visible_messages(self, config: Dict[str, Any]) -> List[Union[BaseMessage, dict]]:
        """
        Retrieves user-visible messages from the stored state.
        Always returns a list; empty if no messages are found.
        """
        runnable_config: RunnableConfig = config
        thread_id = config.get("configurable", {}).get("thread_id")
        print(f"[CHECKPOINTER][aget_user_visible_messages] Getting messages for thread_id: {thread_id}")
        wrapper = await self.aget(config) # aget ensures a default structure

        if not wrapper:
            print(f"  [CHECKPOINTER][aget_user_visible_messages][WARN] Wrapper is None for {thread_id}, returning empty list.")
            return []

        # Prioritize the top-level 'messages' key populated by aget/aput
        messages_data = wrapper.get("messages", [])
        print(f"  [CHECKPOINTER][aget_user_visible_messages] Found {len(messages_data)} messages in top-level 'messages' key.")

        if not messages_data:
            # Fallback to checking channel_values if top-level is empty
            print(f"  [CHECKPOINTER][aget_user_visible_messages] Top-level 'messages' empty, checking channel_values for {thread_id}...")
            channel_values = wrapper.get("channel_values", {})
            if isinstance(channel_values, dict):
                # Check within __default__ channel
                default_channel_state = channel_values.get("__default__", {})
                if isinstance(default_channel_state, dict):
                    messages_data = default_channel_state.get("messages", [])
                    print(f"    Found {len(messages_data)} messages in channel_values.__default__.messages.")
                elif isinstance(default_channel_state, list):
                    messages_data = default_channel_state
                    print(f"    Found {len(messages_data)} messages directly in channel_values.__default__ (list).")

                # Check 'messages' as a separate channel if still not found
                if not messages_data and "messages" in channel_values:
                     candidate = channel_values.get("messages")
                     if isinstance(candidate, list):
                         messages_data = candidate
                         print(f"    Found {len(messages_data)} messages in channel_values.messages.")

        if not isinstance(messages_data, list):
            print(f"  [CHECKPOINTER][aget_user_visible_messages][WARN] Final messages_data is not a list (type: {type(messages_data)}), returning empty list for {thread_id}.")
            return []

        if not messages_data:
            print(f"  [CHECKPOINTER][aget_user_visible_messages][INFO] No messages found in state after checking all locations for {thread_id}, returning empty list.")
            return []

        # Deserialize message data
        deserialized_messages = []
        print(f"  [CHECKPOINTER][aget_user_visible_messages] Deserializing {len(messages_data)} message items for {thread_id}...")
        for i, msg_data in enumerate(messages_data):
            try:
                if isinstance(msg_data, dict) and "type" in msg_data and "content" in msg_data:
                    msg_type = msg_data.get("type")
                    content = msg_data.get("content", "")
                    additional_kwargs = msg_data.get("additional_kwargs", {})
                    if msg_type == "human":
                        deserialized_messages.append(HumanMessage(content=content, additional_kwargs=additional_kwargs))
                    elif msg_type == "ai" or msg_type == "assistant":
                        deserialized_messages.append(AIMessage(content=content, additional_kwargs=additional_kwargs))
                    else:
                        print(f"    [WARN] Keeping unknown message type as dict: {msg_type}")
                        deserialized_messages.append(msg_data)
                elif isinstance(msg_data, BaseMessage):
                    deserialized_messages.append(msg_data)
                else:
                    print(f"    [WARN] Skipping unknown message data format at index {i}: {type(msg_data)}")
            except Exception as e_deserialize:
                 print(f"    [ERROR] Error deserializing message at index {i}: {e_deserialize}, data: {msg_data}")

        print(f"[CHECKPOINTER][aget_user_visible_messages] Returning {len(deserialized_messages)} deserialized messages for {thread_id}.")
        return deserialized_messages

