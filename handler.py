# handler.py
"""AWS Lambda handler using Mangum adapter for FastAPI.

This module provides the entry point for AWS Lambda to invoke
the FastAPI application. Mangum translates API Gateway events
to ASGI format that FastAPI understands.
"""

from mangum import Mangum
from app.main import app

# Create the Lambda handler
# lifespan="off" disables ASGI lifespan events which aren't needed in Lambda
handler = Mangum(app, lifespan="off")
