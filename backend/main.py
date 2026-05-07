import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.tools import router as tools_router
from database import db, ensure_indexes
from config import settings
from middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("perf")

app = FastAPI(
    title="Gemini LangGraph Chatbot API",
    description="AI Chatbot with persistent memory, tools, and background tasks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    response.headers["X-Request-ID"] = request_id

    from services.profiling_service import metrics
    metrics.record_request(request.url.path, duration)

    if duration > 15 and "/api/v1/chat" in request.url.path:
        perf_logger.warning(
            f"[PERF] Chat response exceeded 15s threshold: {duration:.3f}s | request_id={request_id}"
        )

    perf_logger.info(
        f"[PERF] {request.method} {request.url.path} -> {response.status_code} | {duration:.3f}s | request_id={request_id}"
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials="*" not in settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(tools_router, prefix="/api/v1", tags=["Tools"])


@app.on_event("startup")
async def startup_event():
    ensure_indexes()
    logger.info("[STARTUP] MongoDB indexes verified")


@app.get("/")
def home():
    return {
        "message": "Gemini LangGraph Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "metrics": "/metrics",
    }


@app.get("/metrics")
def get_metrics():
    from services.profiling_service import metrics
    return metrics.generate_report()


@app.get("/health")
def health_check():
    health = {
        "status": "healthy",
        "database": "unknown",
        "scheduler": "unknown",
        "gemini": "unknown",
    }

    try:
        db.command("ping")
        health["database"] = "healthy"
    except Exception as e:
        logger.error(f"[HEALTH] Database check failed: {e}")
        health["database"] = "unhealthy"
        health["status"] = "degraded"

    try:
        from services.scheduler_service import scheduler
        if scheduler.running:
            health["scheduler"] = "healthy"
        else:
            health["scheduler"] = "stopped"
            health["status"] = "degraded"
    except Exception as e:
        logger.error(f"[HEALTH] Scheduler check failed: {e}")
        health["scheduler"] = "unhealthy"
        health["status"] = "degraded"

    try:
        from services.gemini_service import get_model
        if get_model():
            health["gemini"] = "healthy"
        else:
            health["gemini"] = "unhealthy"
            health["status"] = "degraded"
    except Exception as e:
        logger.error(f"[HEALTH] Gemini check failed: {e}")
        health["gemini"] = "unhealthy"
        health["status"] = "degraded"

    return health


@app.on_event("shutdown")
async def shutdown_event():
    from services.scheduler_service import scheduler
    scheduler.shutdown()
    logger.info("[SHUTDOWN] Scheduler shut down gracefully")
