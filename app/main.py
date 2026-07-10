import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .controllers import budget, budgets
from .database import engine, Base

app = FastAPI(title="Budget API")

# Configure CORS - explicit origins required when allow_credentials=True.
# Production origins come from the CORS_ORIGINS env var (comma-separated),
# set in /opt/simple-budget/.env on the Oracle VM.
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
)
origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
from sqlalchemy import text
with engine.connect() as connection:
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS budget_v3"))
    connection.commit()

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    """Liveness probe used by systemd/CI deploy health checks."""
    return {"status": "ok"}


# Include routers
app.include_router(budget.router, prefix="/api", tags=["finance"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
