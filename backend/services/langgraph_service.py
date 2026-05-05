import logging
import json
import re
from typing import TypedDict
from fastapi import HTTPException, status
from langgraph.graph import StateGraph, END
from services.gemini_service import get_response
from services.tool_service import find_hospitals
from services.scheduler_service import schedule_task, parse_reminder_delay
from services.memory_service import get_history, save_conversation
from services.profile_service import get_user_profile, update_user_profile
from services.episodic_service import save_episodic_memory, get_episodic_memories

logger = logging.getLogger(__name__)

class ChatState(TypedDict, total=False):
    input: str
    output: str
    session_id: str
    user_id: str


def extract_location_with_gemini(text: str) -> str:
    """Extract location from user input using Gemini for better accuracy"""
    try:
        prompt = f"""Extract the location name from this text. Return ONLY the location name, nothing else.
If no location is mentioned, return "unknown".

Text: {text}

Location:"""
        location = get_response(prompt).strip()
        if location.startswith("Error:"):
            raise ValueError(f"Gemini returned an error: {location}")
        if location.lower() in ["unknown", "none", ""]:
            return "your area"
        return location.title()
    except Exception as e:
        logger.error(f"[LOCATION] Gemini extraction failed: {e}")
        return extract_location_regex(text)

def extract_location_regex(text: str) -> str:
    """Fallback: Extract location from user input using regex patterns"""
    patterns = [
        r'in\s+([A-Za-z\s,]+?)(?:\s*$|[.!?])',
        r'near\s+([A-Za-z\s,]+?)(?:\s*$|[.!?])',
        r'around\s+([A-Za-z\s,]+?)(?:\s*$|[.!?])',
        r'at\s+([A-Za-z\s,]+?)(?:\s*$|[.!?])',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Remove common trailing words
            location = re.sub(r'\s+(please|now|today|tomorrow)$', '', location, flags=re.IGNORECASE)
            return location.title()
    return "your area"


def extract_reminder(text: str) -> str:
    """Extract reminder content from user input using regex patterns"""
    patterns = [
        r'remind me (?:to|about)\s+(.+?)(?:\s+in\s+|\s*$)',
        r'reminder (?:to|for|about)\s+(.+?)(?:\s+in\s+|\s*$)',
        r'don\'?t forget (?:to|about)\s+(.+?)(?:\s+in\s+|\s*$)',
        r'set (?:a )?reminder (?:to|for|about)\s+(.+?)(?:\s+in\s+|\s*$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return "Reminder: " + match.group(1).strip()
    return "Reminder: Your task is complete!"


def tool_node(state: ChatState):
    user_input = state.get("input", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")
    
    # Error handling for missing user_id
    if not user_id:
        logger.error("[TOOL] Missing user_id in state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to use tools"
        )
    
    try:
        location = extract_location_with_gemini(user_input)
        hospitals = find_hospitals(location)
        response = f"Here are some hospitals in {location}:\n" + "\n".join([f"- {h}" for h in hospitals])
        save_conversation(user_id, user_input, response, session_id=session_id)
        
        # Save episodic memory for tool usage
        save_episodic_memory(
            user_id=user_id,
            session_id=session_id,
            event_summary=f"User searched for hospitals in {location}",
            event_type="tool_usage",
            importance_score=0.6
        )
        
        return {"output": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TOOL] Hospital lookup failed: {e}")
        return {"output": "Sorry, I couldn't fetch hospital data. Please try again."}


def scheduler_node(state: ChatState):
    user_input = state.get("input", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")
    
    # Error handling for missing user_id
    if not user_id:
        logger.error("[SCHEDULER] Missing user_id in state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to set reminders"
        )
    
    try:
        reminder_text = extract_reminder(user_input)
        
        delay_seconds, delay_phrase = parse_reminder_delay(user_input)
        if delay_seconds is None:
            response = (
                "I can set that reminder, but please include when you want it. "
                "Examples: 'in 30 minutes', 'in 2 hours', 'tomorrow at 9am', or 'at 18:30'."
            )
            save_conversation(user_id, user_input, response, session_id=session_id)
            return {"output": response}

        schedule_task(user_id, reminder_text, delay=delay_seconds)
        response = f"I've scheduled that for you {delay_phrase}: \"{reminder_text}\""
        save_conversation(user_id, user_input, response, session_id=session_id)
        
        # Save episodic memory for reminder
        save_episodic_memory(
            user_id=user_id,
            session_id=session_id,
            event_summary=f"User set reminder: {reminder_text}",
            event_type="reminder",
            importance_score=0.7
        )
        
        return {"output": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SCHEDULER] Task failed: {e}")
        return {"output": "Failed to set reminder. Please try again."}


def chat_node(state: ChatState):
    user_input = state.get("input", "").strip()
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")
    
    # Error handling for missing user_id
    if not user_id:
        logger.error("[CHAT] Missing user_id in state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to chat"
        )
    
    if not user_input:
        return {"output": "Please enter a message."}
    
    # Get conversation history
    history = get_history(user_id, session_id=session_id)
    
    # Get user profile
    profile = get_user_profile(user_id)
    profile_str = "\n".join([f"- {k}: {v}" for k, v in profile.items()]) if profile else "No details known yet."
    
    # Get episodic memories for context
    episodic_memories = get_episodic_memories(user_id, limit=5, min_importance=0.5)
    episodic_str = ""
    if episodic_memories:
        episodic_str = "\n".join([f"- {m['date']}: {m['summary']}" for m in episodic_memories])
    
    # Build enhanced prompt with episodic memory
    prompt = f"""You are a highly capable AI assistant with long-term memory.
--- USER CONTEXT ---
LONG-TERM FACTS KNOWN ABOUT USER:
{profile_str}

IMPORTANT PAST EVENTS (Episodic Memory):
{episodic_str if episodic_str else "No significant past events recorded yet."}

SHORT-TERM CONVERSATION HISTORY:
{history}
---
USER INPUT: {user_input}

SYSTEM INSTRUCTIONS:
1. Use the facts known about the user to personalize your response.
2. Reference past events from episodic memory when relevant to the conversation.
3. If the user mentions a new personal fact (name, age, city, hobby, preference), you MUST acknowledge it naturally in your reply.
4. CRITICAL: If you learn a new fact, you MUST append a machine-readable block at the VERY END of your response in this EXACT format:
   [EXTRACT: {{"key": "value"}}]
   Example: If they say "I am 20", add [EXTRACT: {{"age": "20"}}] at the end.
5. Keep your conversational response friendly and concise.

Assistant:"""
    
    try:
        response = get_response(prompt)
        clean_response = response
        
        # Extract facts from response
        if "[EXTRACT:" in response:
            try:
                parts = response.split("[EXTRACT:")
                clean_response = parts[0].strip()
                fact_json = parts[1].split("]")[0].strip()
                fact_data = json.loads(fact_json)
                for k, v in fact_data.items():
                    update_user_profile(user_id, k, str(v))
                    logger.info(f"[PROFILE] Extracted fact: {k}={v}")
            except Exception as e:
                logger.error(f"[PROFILE] Extraction failed: {e}")
        
        # Save conversation
        save_conversation(user_id, user_input, clean_response, session_id=session_id)
        
        # Save episodic memory for significant conversations
        # Determine importance based on conversation length and content
        importance = 0.5
        if len(user_input) > 100 or any(word in user_input.lower() for word in ['important', 'remember', 'never forget']):
            importance = 0.8
        
        save_episodic_memory(
            user_id=user_id,
            session_id=session_id,
            event_summary=f"Conversation: {user_input[:100]}...",
            event_type="conversation",
            importance_score=importance
        )
        
        return {"output": clean_response}
    except Exception as e:
        logger.error(f"[CHAT] Failed to generate response: {e}")
        return {"output": "I'm having trouble generating a response right now. Please try again."}


def router_node(state: ChatState):
    """Router node - passes state through"""
    return state


def route_decision(state: ChatState) -> str:
    """Decide which node to route to based on user input"""
    user_input = state.get("input", "").lower()
    
    # Check for hospital search
    if any(word in user_input for word in ["hospital", "clinic", "medical center", "doctor"]):
        return "tool"
    
    # Check for reminder/scheduler
    if any(phrase in user_input for phrase in ["remind me", "reminder", "don't forget", "set a reminder"]):
        return "scheduler"
    
    # Default to chat
    return "chat"


# Build the LangGraph
graph = StateGraph(ChatState)

# Add nodes
graph.add_node("router", router_node)
graph.add_node("chat", chat_node)
graph.add_node("tool", tool_node)
graph.add_node("scheduler", scheduler_node)

# Set entry point
graph.set_entry_point("router")

# Add conditional edges from router
graph.add_conditional_edges(
    "router",
    route_decision,
    {
        "chat": "chat",
        "tool": "tool",
        "scheduler": "scheduler"
    }
)

# Add edges to END
graph.add_edge("chat", END)
graph.add_edge("tool", END)
graph.add_edge("scheduler", END)

# Compile the graph
app_graph = graph.compile()

logger.info("[LANGGRAPH] Graph compiled successfully with episodic memory integration")
