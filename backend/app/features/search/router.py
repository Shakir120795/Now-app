"""Search transport (public)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.search.schemas import SearchResults, SuggestOut, TrendingOut
from app.features.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


async def _optional_user_id(request: Request) -> None:
    # Search is public; personalized logging attaches a user id only if a valid
    # bearer token is present. Kept lightweight to avoid gating public search on auth.
    return None


@router.get("", response_model=SearchResults)
async def search(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).search(q, user_id=None)


@router.get("/suggest", response_model=SuggestOut)
async def suggest(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    return await SearchService(db).suggest(q)


@router.get("/trending", response_model=TrendingOut)
async def trending(db: AsyncSession = Depends(get_db)):
    return await SearchService(db).trending()
