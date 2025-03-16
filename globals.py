from typing import Dict, Any

global_state: Dict[str, Dict[str, Any]] = {}  # Format: {session_id: {"current_task": str, "data": Any}}
model_registry = {}

def init():
    global model_registry, global_state
    model_registry = {}
    global_state = {}
