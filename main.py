import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.migrations import run_admin_upsert
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.calendar import router as calendar_router
from app.api.payments import router as payments_router

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await run_admin_upsert()
            logger.info("Admin upsert completed successfully.")
            break
        except Exception as e:
            logger.warning(
                f"Admin upsert attempt {attempt}/{MAX_RETRIES} failed: {e}"
            )
            if attempt == MAX_RETRIES:
                logger.error(
                    "Admin upsert failed after all retries. "
                    "Make sure Supabase migrations have been applied. Starting anyway."
                )
            else:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
    yield


app = FastAPI(
    title="Trader Pro - User Microservice",
    description="Backend microservice for user management, authentication, calendar, and payment preparation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(calendar_router)
api_router.include_router(payments_router)


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-microservice"}


app.include_router(api_router)
