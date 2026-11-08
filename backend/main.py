"""TalentHub - Campus Placement Management System.

Run:  uvicorn main:app --port 8000      then open http://127.0.0.1:8000
The API lives at the same address (interactive docs: /docs); the dashboard is served from ./static.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import applications, auth, companies, coordinator, jobs, offers, policy, students
from app.core.database import AsyncSessionLocal, init_db
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_if_empty(db)
    yield


app = FastAPI(title="TalentHub Placement Management API", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

for r in (auth, students, companies, jobs, applications, offers, policy, coordinator):
    app.include_router(r.router)


@app.get("/", tags=["meta"])
async def root():
    return {"message": "TalentHub Placement Management API", "docs": "/docs"}


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}



