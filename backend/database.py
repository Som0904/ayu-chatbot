from pymongo import ASCENDING, DESCENDING, MongoClient
from config import settings
from urllib.parse import urlparse

# Initialize MongoClient
client = MongoClient(settings.MONGO_URL)

# Resolve database name explicitly so bad URIs fail early.
parsed = urlparse(settings.MONGO_URL)
db_name = parsed.path.lstrip("/")
if not db_name:
    raise ValueError("MONGO_URL must include a database name, e.g. mongodb://localhost:27017/chatbot_db")

db = client[db_name]

# Collections
conversations_col = db["conversations"]
user_profile_col = db["user_profile"]
notifications_col = db["notifications"]
users_col = db["users"]
episodic_memories_col = db["episodic_memories"]


def ensure_indexes() -> None:
    users_col.create_index([("email", ASCENDING)], unique=True)
    users_col.create_index([("username", ASCENDING)], unique=True)
    users_col.create_index([("id", ASCENDING)], unique=True, sparse=True)
    users_col.create_index([("created_at", DESCENDING)])

    conversations_col.create_index([("user_id", ASCENDING), ("session_id", ASCENDING), ("created_at", DESCENDING)])
    conversations_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    notifications_col.create_index([("user_id", ASCENDING), ("is_read", ASCENDING), ("created_at", DESCENDING)])
    notifications_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    user_profile_col.create_index([("user_id", ASCENDING), ("key", ASCENDING)], unique=True)

    episodic_memories_col.create_index([("user_id", ASCENDING), ("importance_score", DESCENDING), ("created_at", DESCENDING)])
    episodic_memories_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
