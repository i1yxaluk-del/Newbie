import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import auth, content, leads
from .services.seed import run_seed

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.APP_NAME, "env": settings.APP_ENV}


app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(content.router)
