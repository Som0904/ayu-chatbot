import logging
from datetime import datetime, timezone, timedelta
from database import episodic_memories_col

logger = logging.getLogger(__name__)

def save_episodic_memory(user_id: str, session_id: str, event_summary: str, event_type: str = "conversation", importance_score: float = 0.5):
    """Save an episodic memory to MongoDB"""
    try:
        memory = {
            "user_id": user_id,
            "session_id": session_id,
            "event_summary": event_summary,
            "event_type": event_type,
            "importance_score": importance_score,
            "created_at": datetime.now(timezone.utc)
        }
        episodic_memories_col.insert_one(memory)
        logger.info(f"[EPISODIC] Saved memory for user {user_id}: {event_summary[:50]}...")
    except Exception as e:
        logger.error(f"[EPISODIC] Failed to save memory: {e}")

def get_episodic_memories(user_id: str, limit: int = 10, min_importance: float = 0.3):
    """Retrieve episodic memories from MongoDB"""
    try:
        docs = episodic_memories_col.find({
            "user_id": user_id,
            "importance_score": {"$gte": min_importance}
        }).sort([("importance_score", -1), ("created_at", -1)]).limit(limit)
        
        return [
            {
                "summary": m["event_summary"],
                "type": m["event_type"],
                "importance": m["importance_score"],
                "date": m["created_at"].strftime("%Y-%m-%d")
            }
            for m in docs
        ]
    except Exception as e:
        logger.error(f"[EPISODIC] Failed to retrieve memories: {e}")
        return []

def get_recent_episodic_memories(user_id: str, days: int = 7, limit: int = 5):
    """Get recent episodic memories from MongoDB"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        docs = episodic_memories_col.find({
            "user_id": user_id,
            "created_at": {"$gte": cutoff_date}
        }).sort("created_at", -1).limit(limit)
        
        return [
            {
                "summary": m["event_summary"],
                "type": m["event_type"],
                "date": m["created_at"].strftime("%Y-%m-%d %H:%M")
            }
            for m in docs
        ]
    except Exception as e:
        logger.error(f"[EPISODIC] Failed to retrieve recent memories: {e}")
        return []

def summarize_session_to_episodic(user_id: str, session_id: str):
    """Summarize a conversation session into an episodic memory"""
    from services.memory_service import get_history
    
    history = get_history(user_id, session_id=session_id, limit=20)
    
    if not history or len(history) < 50:
        return
    
    lines = history.split('\n')
    user_messages = [line for line in lines if line.startswith('User:')]
    
    if len(user_messages) > 0:
        first_msg = user_messages[0].replace('User:', '').strip()
        last_msg = user_messages[-1].replace('User:', '').strip()
        
        summary = f"Conversation about: {first_msg[:100]}"
        if len(user_messages) > 1:
            summary += f" ... {last_msg[:100]}"
        
        importance = min(0.9, 0.3 + (len(user_messages) * 0.05))
        
        save_episodic_memory(
            user_id=user_id,
            session_id=session_id,
            event_summary=summary,
            event_type="conversation",
            importance_score=importance
        )
        logger.info(f"[EPISODIC] Created session summary for user {user_id}, session {session_id}")
