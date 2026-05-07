import logging
import time
import threading
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

logger.info(f"[GEMINI] Initialized model: {settings.GEMINI_MODEL}")


class GeminiAuthError(Exception):
    pass


class GeminiRateLimitError(Exception):
    pass


class GeminiServiceError(Exception):
    pass


_GEMINI_CONFIG_LOCK = threading.Lock()


def get_model(api_key: str | None = None):
    key_to_use = api_key.strip() if api_key else settings.GEMINI_API_KEY
    genai.configure(api_key=key_to_use)
    return genai.GenerativeModel(settings.GEMINI_MODEL)


def get_response(prompt: str, api_key: str | None = None) -> str:
    for attempt in range(1, settings.RATE_LIMIT_MAX_RETRIES + 1):
        try:
            logger.debug(f"[GEMINI] Sending prompt (attempt {attempt}, len={len(prompt)} chars)")
            start_time = time.time()
            # google.generativeai uses global configuration; lock prevents cross-request key races.
            with _GEMINI_CONFIG_LOCK:
                model = get_model(api_key=api_key)
                response = model.generate_content(prompt)
            duration = time.time() - start_time

            try:
                from services.profiling_service import metrics
                metrics.record_gemini_call(duration)
            except Exception:
                pass

            if response.candidates:
                text = response.candidates[0].content.parts[0].text
                if not text or not text.strip():
                    logger.warning("[GEMINI] Model returned empty text in candidate")
                    return "I received an empty response. Please try again."
                return text
            else:
                logger.warning("[GEMINI] No candidates returned by model")
                return "No response from model"

        except Exception as e:
            error_str = str(e)

            if "429" in error_str or "quota" in error_str.lower():
                wait = settings.RATE_LIMIT_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    f"[GEMINI] Rate limit hit (attempt {attempt}/{settings.RATE_LIMIT_MAX_RETRIES}). "
                    f"Waiting {wait}s before retry..."
                )
                if attempt < settings.RATE_LIMIT_MAX_RETRIES:
                    time.sleep(wait)
                    continue
                else:
                    logger.error("[GEMINI] All retry attempts exhausted due to rate limiting.")
                    raise GeminiRateLimitError("Gemini rate limit exceeded")

            if "API_KEY_INVALID" in error_str or "API key expired" in error_str or "invalid api key" in error_str.lower():
                logger.warning("[GEMINI] API key validation failed")
                raise GeminiAuthError("Invalid or expired Gemini API key")

            logger.error("[GEMINI] Generation failed (non-retryable)")
            raise GeminiServiceError("Gemini generation failed")

    raise GeminiServiceError("Unexpected Gemini error")
