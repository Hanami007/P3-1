import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import announcements, buildings, cards, chatbot, logs, presence, schedule
from app.services import camera_wake

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CS Smart Kiosk API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(schedule.router)
app.include_router(buildings.router)
app.include_router(announcements.router)
app.include_router(chatbot.router)
app.include_router(logs.router)
app.include_router(presence.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    camera_wake.start()


@app.on_event("shutdown")
def on_shutdown():
    camera_wake.stop()


@app.get("/api/health")
def health():
    return {"status": "ok"}
