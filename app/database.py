# database.py
"""Database configuration and session management."""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from the .env file
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please set it in your .env file or environment."
    )

logger.info("Connecting to database...")

# Create the SQLAlchemy engine.
# The app now runs as a long-lived process on the Oracle VM, so use a real
# connection pool (NullPool was only appropriate for Lambda cold starts).
# pool_pre_ping/pool_recycle keep connections healthy across Supabase's
# idle-connection timeouts.
engine = create_engine(
    DATABASE_URL,
    client_encoding='utf8',
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

