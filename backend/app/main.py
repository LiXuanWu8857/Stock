from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import create_tables
from app.routers import holdings, transactions, quotes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stock Portfolio API",
    description="Stock portfolio management system API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(holdings.router)
app.include_router(transactions.router)
app.include_router(quotes.router)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    logger.info("Starting up Stock Portfolio API...")
    try:
        await create_tables()
        logger.info("Database tables created/verified successfully")

        # Ensure default user exists
        from app.database import AsyncSessionLocal
        from app.models.models import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
            if not user:
                user = User(id=1, email="user@example.com", name="Portfolio Owner")
                db.add(user)
                await db.commit()
                logger.info("Default user created")

    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.get("/")
async def root():
    return {"message": "Stock Portfolio API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
