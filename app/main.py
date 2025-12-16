from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .controllers import budget, budgets
from .database import engine, Base

app = FastAPI(title="Budget API")

# Configure CORS - explicit origins required when allow_credentials=True
origins = [
    "https://d1wqjnlllq13dm.cloudfront.net",  # Production CloudFront
    "http://localhost:5173",                    # Local development
    "http://localhost:3000",                    # Alternative local dev
]

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

# Include routers
app.include_router(budget.router, prefix="/api", tags=["finance"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
