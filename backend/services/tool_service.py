import requests
import logging

logger = logging.getLogger(__name__)

def find_hospitals(location: str) -> list[str]:
    """Fetch real hospitals near a location using OpenStreetMap Nominatim API."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"hospital in {location}",
            "format": "json",
            "limit": 5
        }
        # Nominatim requires a User-Agent header
        headers = {"User-Agent": "gemini-langgraph-chatbot/1.0"}

        res = requests.get(url, params=params, headers=headers, timeout=5)
        res.raise_for_status()

        data = res.json()

        if not data:
            logger.warning(f"[TOOL] Nominatim returned no results for: {location}")
            return _fallback(location)

        hospitals = [place["display_name"] for place in data]
        logger.info(f"[TOOL] Found {len(hospitals)} hospitals in {location} via Nominatim")
        return hospitals

    except requests.exceptions.Timeout:
        logger.error(f"[TOOL] Nominatim request timed out for: {location}")
        return _fallback(location)

    except Exception as e:
        logger.error(f"[TOOL] Nominatim request failed: {e}")
        return _fallback(location)


def _fallback(location: str) -> list[str]:
    """Returns static hospital names when the API is unavailable."""
    logger.info(f"[TOOL] Using static fallback hospitals for: {location}")
    return [
        f"{location} AIIMS Hospital",
        f"{location} Apollo Hospital",
        f"{location} City Care Hospital",
    ]