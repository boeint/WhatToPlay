"""The WhatToPlay web app.

Run locally:
    uvicorn app.main:app --reload
then open http://localhost:8000/docs
"""
from fastapi import FastAPI

from app.routers import franchises, platforms

app = FastAPI(title="WhatToPlay", version="0.1.0")

app.include_router(platforms.router)
app.include_router(franchises.router)
