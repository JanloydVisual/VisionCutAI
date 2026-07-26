from typing import Dict, List, Optional
from core.ai.object_session import ObjectSession

class ObjectManager:
    """
    Manages multiple ObjectSessions, handling creation, selection, and multi-object mask aggregation.
    """
    def __init__(self):
        self.sessions: Dict[str, ObjectSession] = {}
        self.active_object_id: Optional[str] = None
        self._next_id = 1
        
    def create_object(self, name: Optional[str] = None) -> ObjectSession:
        obj_id = f"{self._next_id:03d}"
        self._next_id += 1
        
        session = ObjectSession(object_id=obj_id, object_name=name or f"Object {obj_id}")
        self.sessions[obj_id] = session
        
        if self.active_object_id is None:
            self.active_object_id = obj_id
            
        return session
        
    def remove_object(self, obj_id: str):
        if obj_id in self.sessions:
            del self.sessions[obj_id]
            if self.active_object_id == obj_id:
                self.active_object_id = list(self.sessions.keys())[0] if self.sessions else None
                
    def switch_active_object(self, obj_id: str):
        if obj_id in self.sessions:
            self.active_object_id = obj_id
            
    def get_active_session(self) -> Optional[ObjectSession]:
        if self.active_object_id:
            return self.sessions.get(self.active_object_id)
        return None
        
    def get_all_sessions(self) -> List[ObjectSession]:
        return list(self.sessions.values())
