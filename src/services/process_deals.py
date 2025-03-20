import MT5Manager
import asyncio
import traceback
import time

from datetime import datetime
from typing import List, Tuple
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import delete
from models import DealTask, MT5Deal, DealStatus
from libs.manager import get_mt5_manager

# Define the most important columns for display
DISPLAY_COLUMNS = [
    "deal_id",
    "time",
    "symbol",
    "login",
    "action",
    "entry",
    "price",
    "volume",
    "profit",
    "comment",
]


def chunk_list(lst, chunk_size):
    """Split a list into chunks of specified size"""
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def convert_mt5_timestamp(timestamp: int) -> datetime:
    """Convert MT5 timestamp to Python datetime"""
    return datetime.fromtimestamp(timestamp)


async def process_single_deal(
    deal: DealTask,
    account_numbers: List[str],
    manager: MT5Manager.ManagerAPI,
    session: AsyncSession,
):
    # Create a new session for each task to avoid concurrency issues
    try:
        # Delete all deals for this task directly
        stmt = delete(MT5Deal).where(MT5Deal.deal_task_id == deal.id)
        await session.exec(stmt)
        await session.commit()

        # Convert deal date and times to datetime objects
        start_datetime = datetime.combine(deal.date, deal.start_time)
        end_datetime = datetime.combine(deal.date, deal.end_time)

        # Use the deal's start and end datetime with pre-fetched account numbers
        mt_deals = manager.DealRequestByLogins(
            account_numbers, start_datetime, end_datetime
        )

        if not mt_deals:
            error = MT5Manager.LastError()
            print(
                f"[ERROR] No deals found or error occurred for task {deal.id}. MT5 Error: {error}"
            )
            return False, deal.id

        total_deals = len(mt_deals)

        if total_deals > 0:
            # Process in larger chunks for better performance - 500 deals per chunk
            CHUNK_SIZE = 500
            chunks = chunk_list(mt_deals, CHUNK_SIZE)
            total_chunks = len(chunks)

            for chunk_idx, chunk in enumerate(chunks, 1):
                mt5_deals_to_insert = []

                for mt_deal in chunk:
                    # Convert timestamps to datetime objects
                    deal_time = convert_mt5_timestamp(mt_deal.Time)

                    # Create MT5Deal object
                    new_deal = MT5Deal(
                        deal_id=mt_deal.Deal,
                        action=mt_deal.Action,
                        comment=mt_deal.Comment,
                        commission=mt_deal.Commission,
                        contract_size=mt_deal.ContractSize,
                        dealer=mt_deal.Dealer,
                        digits=mt_deal.Digits,
                        digits_currency=mt_deal.DigitsCurrency,
                        entry=mt_deal.Entry,
                        expert_id=mt_deal.ExpertID,
                        external_id=mt_deal.ExternalID,
                        fee=mt_deal.Fee,
                        flags=mt_deal.Flags,
                        gateway=mt_deal.Gateway,
                        login=mt_deal.Login,
                        market_ask=mt_deal.MarketAsk,
                        market_bid=mt_deal.MarketBid,
                        market_last=mt_deal.MarketLast,
                        modification_flags=mt_deal.ModificationFlags,
                        obsolete_value=mt_deal.ObsoleteValue,
                        order_id=mt_deal.Order,
                        position_id=mt_deal.PositionID,
                        price=mt_deal.Price,
                        price_gateway=mt_deal.PriceGateway,
                        price_position=mt_deal.PricePosition,
                        price_sl=mt_deal.PriceSL,
                        price_tp=mt_deal.PriceTP,
                        profit=mt_deal.Profit,
                        profit_raw=mt_deal.ProfitRaw,
                        rate_margin=mt_deal.RateMargin,
                        rate_profit=mt_deal.RateProfit,
                        reason=mt_deal.Reason,
                        storage=mt_deal.Storage,
                        symbol=mt_deal.Symbol,
                        tick_size=mt_deal.TickSize,
                        tick_value=mt_deal.TickValue,
                        time=deal_time,
                        time_msc=mt_deal.TimeMsc,
                        value=mt_deal.Value,
                        volume=mt_deal.Volume,
                        volume_closed=mt_deal.VolumeClosed,
                        volume_closed_ext=mt_deal.VolumeClosedExt,
                        volume_ext=mt_deal.VolumeExt,
                        deal_task_id=deal.id,
                    )
                    mt5_deals_to_insert.append(new_deal)

                # Process sub-chunks for better timeout handling
                SUB_CHUNK_SIZE = 100  # Increased from 25 to 100
                sub_chunks = [
                    mt5_deals_to_insert[i : i + SUB_CHUNK_SIZE]
                    for i in range(0, len(mt5_deals_to_insert), SUB_CHUNK_SIZE)
                ]

                for sub_chunk in sub_chunks:
                    retry_count = 0
                    max_retries = 2  # Reduced from 3 to 2
                    while retry_count < max_retries:
                        try:
                            session.add_all(sub_chunk)
                            await asyncio.wait_for(
                                session.commit(), timeout=45
                            )  # Increased timeout
                            break
                        except asyncio.TimeoutError:
                            print(
                                f"[WARNING] Timeout on attempt {retry_count + 1} for chunk {chunk_idx}"
                            )
                            await session.rollback()
                            retry_count += 1
                            if retry_count == max_retries:
                                print(
                                    f"[ERROR] Failed after {max_retries} attempts for chunk {chunk_idx}"
                                )
                                return False, deal.id
                            await asyncio.sleep(0.5)  # Reduced from 1 to 0.5 seconds
                        except Exception as e:
                            print(f"[ERROR] Failed to insert sub-chunk: {str(e)}")
                            await session.rollback()
                            return False, deal.id

                # Clear memory after successful insertion
                mt5_deals_to_insert.clear()

        return True, deal.id
    except Exception as e:
        print(f"[ERROR] Failed to process deal task {deal.id}")
        print(f"[ERROR] Error details: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False, deal.id


async def process_deals(
    deal_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Process multiple deals sequentially to avoid concurrency issues."""
    manager = None
    successful_deals = []
    failed_deals = []

    try:
        # Get deals from database
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        results = await session.exec(statement)
        deals = results.all()

        # Update status to processing for all deals
        for deal in deals:
            deal.status = DealStatus.PROCESSING
        await session.commit()

        # Get direct manager instance
        manager = get_mt5_manager()

        # Get account groups
        total_accounts_group = manager.UserGetByGroup("demo\\Nostro\\*")
        account_numbers = [account.Login for account in total_accounts_group]

        # Process deals sequentially to avoid concurrency issues
        for deal in deals:
            success, deal_id = await process_single_deal(
                deal, account_numbers, manager, session
            )
            if success:
                successful_deals.append(deal_id)
            else:
                failed_deals.append(deal_id)

            # Add a short delay between processing tasks
            await asyncio.sleep(0.1)

        # Update statuses in database
        if successful_deals:
            statement = select(DealTask).where(DealTask.id.in_(successful_deals))
            results = await session.exec(statement)
            success_deals = results.all()

            for deal in success_deals:
                deal.status = DealStatus.SUCCESS

        if failed_deals:
            statement = select(DealTask).where(DealTask.id.in_(failed_deals))
            results = await session.exec(statement)
            failed_deals_db = results.all()

            for deal in failed_deals_db:
                deal.status = DealStatus.FAILED

        await session.commit()

        return len(failed_deals) == 0, successful_deals, failed_deals

    except Exception as e:
        print(f"[ERROR] Error in process_deals: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

        # Update all deals to failed status in case of unexpected error
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        results = await session.exec(statement)
        failed_deals_db = results.all()

        for deal in failed_deals_db:
            deal.status = DealStatus.FAILED

        await session.commit()
        return False, [], deal_ids
    finally:
        if manager:
            manager.Disconnect()
