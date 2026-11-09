import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import agents, analytics, auth, donors, invitations, requests
from app.agents.orchestrator import expire_stale_invitations
from app.core.config import get_settings
from app.core.responses import http_exception_handler, ok, validation_exception_handler
from app.db.session import SessionLocal

settings = get_settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bloodbridge")


def _sweep_once() -> int:
    db = SessionLocal()
    try:
        return expire_stale_invitations(db)
    finally:
        db.close()


async def _follow_up_loop() -> None:
    """Background Follow-up Agent: expires unanswered invitations and finds alternatives."""
    while True:
        await asyncio.sleep(settings.follow_up_interval_seconds)
        try:
            expired = await run_in_threadpool(_sweep_once)
            if expired:
                log.info("Follow-up sweep expired %s invitation(s)", expired)
        except Exception:
            log.exception("Follow-up sweep failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_follow_up_loop()) if settings.enable_background_follow_up else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="BloodBridge AI - agentic blood request coordination (hackathon prototype, synthetic data only, "
                "no clinical decisions).",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

for r in (auth.router, requests.router, donors.router, invitations.router, agents.router, analytics.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["Health"])
def health():
    return ok({"status": "ok", "llm_enabled": settings.llm_enabled}, "BloodBridge API is running")
