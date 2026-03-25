from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from app.core.config import settings
from app.api.api import api_router
from app.db.database import engine
from app.db.base_class import Base
# Import all models to ensure they are registered with Base.metadata
from app.models.user import Users
from app.models.yandex_connection import YandexConnections
from app.models.parsed_receipt import ParsedReceipts
from app.models.subscription import Subscriptions

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "project": settings.PROJECT_NAME}
