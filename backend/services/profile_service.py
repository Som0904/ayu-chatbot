import logging
import json
from database import user_profile_col

logger = logging.getLogger(__name__)


def save_fact(user_id: str, key: str, value: str):
    """Save or update a fact for a user using upsert"""
    try:
        user_profile_col.update_one(
            {"user_id": user_id, "key": key}, {"$set": {"value": value}}, upsert=True
        )
        logger.info(f"[PROFILE] Saved fact {key} for user {user_id}")
    except Exception as e:
        logger.error(f"[PROFILE] Failed to save fact for user {user_id}: {e}")
        raise


def get_all_facts(user_id: str) -> dict:
    """Retrieve all facts for a user as a dictionary"""
    try:
        docs = user_profile_col.find({"user_id": user_id})
        return {d["key"]: d["value"] for d in docs}
    except Exception as e:
        logger.error(f"[PROFILE] Failed to fetch facts for user {user_id}: {e}")
        return {}


def get_user_profile(user_id: str) -> dict:
    """Legacy wrapper for compatibility"""
    return get_all_facts(user_id)


def update_user_profile(user_id: str, key: str, value: str):
    """Legacy wrapper for compatibility"""
    if key == "age":
        try:
            age = int(value)
            if age < 0 or age > 150:
                raise ValueError("Age must be between 0 and 150")
            value = age
        except ValueError:
            raise ValueError(f"Invalid age: {value}")

    save_fact(user_id, key, value)


def create_user_profile(user_id: str):
    """Profile is now dynamic with MongoDB, so we don't strictly need this, but kept for compatibility"""
    return {}
