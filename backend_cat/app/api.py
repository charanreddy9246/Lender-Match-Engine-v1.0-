"""The one HTTP endpoint this app has."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repository import LenderRepository, SqlLenderRepository
from app.schemas import BorrowerProfileIn, MatchResponse
from app.service import match_lenders


def get_lender_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> LenderRepository:
    return SqlLenderRepository(db)


api_router = APIRouter(prefix="/api/v1")


@api_router.post("/lenders/match", response_model=MatchResponse, tags=["lenders"])
async def match(
    profile: BorrowerProfileIn,
    repository: Annotated[LenderRepository, Depends(get_lender_repository)],
) -> MatchResponse:
    return await match_lenders(profile, repository)
