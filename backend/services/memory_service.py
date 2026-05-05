import logging
import time
from datetime import datetime, timezone
from database import conversations_col
from config import settings

logger = logging.getLogger(__name__)

def save_conversation(user_id: str, user_input: str, bot_response: str, session_id: str = "default") -> None:
    try:
        convo = {
            "user_id": user_id,
            "user_input": user_input,
            "bot_response": bot_response,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc)
        }
        start = time.time()
        conversations_col.insert_one(convo)
        duration = time.time() - start
        
        try:
            from services.profiling_service import metrics
            metrics.record_db_operation(duration)
        except:
            pass
        
        logger.info(
            f"[MEMORY] Saved convo | user_id={user_id} | session={session_id} | input_len={len(user_input)} | db_time={duration:.3f}s"
        )
    except Exception as e:
        logger.error(f"[MEMORY] Failed to save conversation: {e}")
        raise

def get_history(user_id: str, session_id: str = "default", limit: int = None) -> str:
    if limit is None:
        limit = settings.MAX_HISTORY_LIMIT
    
    try:
        start = time.time()
        docs = conversations_col.find(
            {"user_id": user_id, "session_id": session_id}
        ).sort("created_at", -1).limit(limit)
        
        convos = list(docs)
        logger.info(f"[MEMORY] get_history | user_id={user_id} | session={session_id} | rows={len(convos)} | db_time={time.time()-start:.3f}s")
        
        history = ""
        for c in reversed(convos):
            history += f"User: {c['user_input']}\nBot: {c['bot_response']}\n"
        return history
    except Exception as e:
        logger.error(f"[MEMORY] Failed to retrieve history for user {user_id}, session {session_id}: {e}")
        return ""

def get_all_sessions(user_id: str):
    try:
        session_ids = conversations_col.distinct("session_id", {"user_id": user_id})
        
        result = []
        for sid in session_ids:
            first_convo = conversations_col.find_one(
                {"user_id": user_id, "session_id": sid}, 
                sort=[("created_at", 1)]
            )
            last_convo = conversations_col.find_one(
                {"user_id": user_id, "session_id": sid}, 
                sort=[("created_at", -1)]
            )
            
            result.append({
                "id": sid,
                "last_active": last_convo["created_at"] if last_convo else None,
                "first_message": first_convo["user_input"] if first_convo else None
            })
            
        return sorted(result, key=lambda x: x["last_active"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    except Exception as e:
        logger.error(f"[MEMORY] Failed to get sessions for user {user_id}: {e}")
        return []

def delete_session(user_id: str, session_id: str):
    try:
        conversations_col.delete_many({"user_id": user_id, "session_id": session_id})
        logger.info(f"[MEMORY] Deleted session {session_id} for user {user_id}")
    except Exception as e:
        logger.error(f"[MEMORY] Failed to delete session {session_id} for user {user_id}: {e}")
        raise
