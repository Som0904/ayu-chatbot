import logging
import time
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel(settings.GEMINI_MODEL)

logger.info(f"[GEMINI] Initialized model: {settings.GEMINI_MODEL}")


def get_response(prompt: str) -> str:
    for attempt in range(1, settings.RATE_LIMIT_MAX_RETRIES + 1):
        try:
            logger.debug(f"[GEMINI] Sending prompt (attempt {attempt}, len={len(prompt)} chars)")
            
            start_time = time.time()
            response = model.generate_content(prompt)
            duration = time.time() - start_time
            
            # Record metrics
            try:
                from services.profiling_service import metrics
                metrics.record_gemini_call(duration)
            except:
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
                    return "The AI service is currently rate-limited. Please wait a moment and try again."

            logger.error(f"[GEMINI] Generation failed (non-retryable): {e}")
            return f"Error: {error_str}"

    return "Unexpected error: no response generated."