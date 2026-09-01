from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin_api import admin_router
from app.api import api_router
from app.config import settings
from app.database import create_all_tables
from app.explore_api import explore_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_all_tables()
    yield


app = FastAPI(title="Find Best Lender API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(admin_router)
app.include_router(explore_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
