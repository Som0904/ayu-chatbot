from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
import time
import logging
from datetime import datetime, timezone, timedelta
import re
import uuid
from database import notifications_col, users_col
from services.email_service import send_notification_email

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    jobstores={
        "default": MongoDBJobStore(database=notifications_col.database.name, collection="scheduled_jobs", client=notifications_col.database.client)
    }
)
scheduler.start()

def send_notification(user_id: str, message: str):
    logger.info(f"[SCHEDULER] Task complete for user {user_id}: {message}")
    
    try:
        notif = {
            "user_id": user_id,
            "message": message,
            "notification_type": "reminder",
            "is_read": False,
            "is_emailed": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        res = notifications_col.insert_one(notif)
        notif_id = res.inserted_id
        
        user = users_col.find_one({"id": user_id})
        if user and user.get("email"):
            email_sent = send_notification_email(user["email"], user["username"], message)
            if email_sent:
                notifications_col.update_one({"_id": notif_id}, {"$set": {"is_emailed": True}})
                logger.info(f"[SCHEDULER] Email sent to {user['email']}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to save notification for user {user_id}: {e}")

def _extract_clock_time(text: str):
    match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if meridiem:
        if hour < 1 or hour > 12:
            return None
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
    elif hour > 23:
        return None

    if minute > 59:
        return None

    return hour, minute


def parse_reminder_delay(user_input: str):
    text = user_input.lower()

    relative_patterns = [
        (r"\bin\s+(\d+)\s*seconds?\b", 1, "seconds"),
        (r"\bin\s+(\d+)\s*minutes?\b", 60, "minutes"),
        (r"\bin\s+(\d+)\s*hours?\b", 3600, "hours"),
        (r"\bin\s+(\d+)\s*days?\b", 24 * 3600, "days"),
    ]

    for pattern, multiplier, unit in relative_patterns:
        match = re.search(pattern, text)
        if match:
            seconds = int(match.group(1)) * multiplier
            return max(5, seconds), f"in {match.group(1)} {unit}"

    now = datetime.now()
    time_part = _extract_clock_time(text)

    if "tomorrow" in text:
        if time_part:
            run_at = (now + timedelta(days=1)).replace(hour=time_part[0], minute=time_part[1], second=0, microsecond=0)
        else:
            run_at = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return int((run_at - now).total_seconds()), run_at.strftime("tomorrow at %I:%M %p")

    if time_part:
        run_at = now.replace(hour=time_part[0], minute=time_part[1], second=0, microsecond=0)
        if run_at <= now:
            run_at = run_at + timedelta(days=1)
        return int((run_at - now).total_seconds()), run_at.strftime("at %I:%M %p")

    return None, None


def schedule_task(user_id: str, message: str, delay: int = 600):
    run_time = time.time() + delay
    run_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(run_time))
    job_id = f"reminder_{user_id}_{uuid.uuid4().hex[:12]}"

    scheduler.add_job(
        send_notification,
        'date',
        run_date=run_date,
        args=[user_id, message],
        id=job_id,
        replace_existing=False,
        misfire_grace_time=300
    )
    logger.info(f"[SCHEDULER] Task scheduled in {delay}s for user {user_id}: {message} (job_id={job_id})")
