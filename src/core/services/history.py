import logging
from typing import List, Dict, Any
from src.core.database import SupabaseRepository

logger = logging.getLogger("HistoryService")

class HistoryService:
    """
    Service responsible for managing chat history and context.
    """

    def __init__(self, db: SupabaseRepository):
        self.db = db

    def get_formatted_history(self, session_id: str, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves and formats history for LLM consumption.
        """
        try:
            raw_history = self.db.get_history(session_id, user_id, limit)
            formatted_history = []
            
            for turn in raw_history:
                # Ensure structure matches genai requirements
                formatted_history.append({
                    "role": turn["role"],
                    "parts": turn["parts"] # Assumed to be list of strings
                })
            
            return formatted_history
        except Exception as e:
            logger.error(f"Failed to load history for session {session_id}: {e}")
            return []

    async def prune_history_async(self, current_history: List[Any], max_length: int = 20):
        """
        Future implementation for history pruning.
        Currently handled by StrategicMemory consolidation within the Agent.
        """
        pass
