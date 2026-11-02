"""Sheet import endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.ingestion.sheet_import import import_from_sheet
from app.models.user import User

router = APIRouter(prefix="/sheet", tags=["sheet-import"])


class SheetImportRequest(BaseModel):
    sheet_url: str


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_sheet(
    body: SheetImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await import_from_sheet(db, current_user.id, body.sheet_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "message": "Import complete",
        "inserted": result["inserted"],
        "skipped": result["skipped"],
    }
