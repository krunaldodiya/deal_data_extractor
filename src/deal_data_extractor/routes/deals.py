from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from deal_data_extractor.database import get_session
from deal_data_extractor.models import DealTask, DealStatus
from deal_data_extractor.services.process_deals import process_deals

router = APIRouter()


@router.post("/process")
async def process_selected_deals(
    deal_ids: List[int], session: AsyncSession = Depends(get_session)
) -> dict:
    """Process selected deals."""
    if not deal_ids:
        raise HTTPException(status_code=400, detail="No deals selected for processing")

    success, successful_deals, failed_deals = await process_deals(deal_ids, session)

    return {
        "success": success,
        "message": "Processing complete",
        "successful_deals": successful_deals,
        "failed_deals": failed_deals,
    }
