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
    try:
        print(f"[DEBUG] Starting to process deal task ID: {deal.id}")
        print(f"[DEBUG] Deleting existing deals for task ID: {deal.id}")
        # Delete all deals for this task directly
        stmt = delete(MT5Deal).where(MT5Deal.deal_task_id == deal.id)
        await session.exec(stmt)
        await session.commit()
        print(f"[DEBUG] Successfully deleted existing deals for task ID: {deal.id}")

        # Convert deal date and times to datetime objects
        start_datetime = datetime.combine(deal.date, deal.start_time)
        end_datetime = datetime.combine(deal.date, deal.end_time)
        print(
            f"[DEBUG] Requesting deals from MT5 for task {deal.id} between {start_datetime} and {end_datetime}"
        )

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
        print(f"[DEBUG] Found {total_deals} deals for task {deal.id}")

        if total_deals > 0:
            # Process in smaller chunks for better performance - 200 deals per chunk
            CHUNK_SIZE = 200  # Reduced from 1000 to 200 for better performance
            chunks = chunk_list(mt_deals, CHUNK_SIZE)
            total_chunks = len(chunks)
            print(f"[DEBUG] Processing {total_chunks} chunks for task {deal.id}")

            # Process and insert each chunk
            for chunk_idx, chunk in enumerate(chunks, 1):
                chunk_start_time = time.time()
                print(
                    f"[DEBUG] Processing chunk {chunk_idx}/{total_chunks} for task {deal.id}"
                )
                chunk_volume = 0
                chunk_profit = 0
                symbols = set()
                logins = set()

                # Create MT5Deal objects for the chunk
                mt5_deals_to_insert = []

                for mt_deal in chunk:
                    # Collect summary data
                    chunk_volume += mt_deal.Volume
                    chunk_profit += mt_deal.Profit
                    symbols.add(mt_deal.Symbol)
                    logins.add(mt_deal.Login)

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

                try:
                    # Set a timeout for database operations to prevent hanging
                    print(f"[DEBUG] Starting database insertion for chunk {chunk_idx}")

                    # Insert all deals in the chunk with timeout
                    session.add_all(mt5_deals_to_insert)
                    # Use asyncio.wait_for to add a timeout
                    try:
                        await asyncio.wait_for(
                            session.commit(), timeout=60
                        )  # 60 second timeout
                    except asyncio.TimeoutError:
                        print(
                            f"[ERROR] Database operation timed out for chunk {chunk_idx}"
                        )
                        await session.rollback()
                        # Try again with a smaller batch
                        if len(mt5_deals_to_insert) > 50:
                            print(f"[DEBUG] Retrying with smaller batches")
                            # Split into smaller batches of 50
                            small_batches = [
                                mt5_deals_to_insert[i : i + 50]
                                for i in range(0, len(mt5_deals_to_insert), 50)
                            ]
                            for batch_idx, small_batch in enumerate(small_batches):
                                try:
                                    session.add_all(small_batch)
                                    await asyncio.wait_for(session.commit(), timeout=30)
                                    print(
                                        f"[DEBUG] Successfully inserted small batch {batch_idx+1}/{len(small_batches)}"
                                    )
                                except Exception as batch_e:
                                    print(
                                        f"[ERROR] Failed to insert small batch: {str(batch_e)}"
                                    )
                                    await session.rollback()

                    chunk_end_time = time.time()
                    chunk_duration = chunk_end_time - chunk_start_time
                    print(
                        f"[DEBUG] Successfully inserted chunk {chunk_idx}/{total_chunks} for task {deal.id} in {chunk_duration:.2f} seconds"
                    )
                    print(
                        f"[DEBUG] Chunk summary - Volume: {chunk_volume}, Profit: {chunk_profit}"
                    )
                    print(f"[DEBUG] Symbols in chunk: {', '.join(symbols)}")
                    print(f"[DEBUG] Number of unique logins in chunk: {len(logins)}")
                except Exception as e:
                    print(
                        f"[ERROR] Failed to insert chunk {chunk_idx}/{total_chunks} for task {deal.id}"
                    )
                    print(f"[ERROR] Error details: {str(e)}")
                    print(f"[ERROR] Traceback: {traceback.format_exc()}")
                    await session.rollback()
                    return False, deal.id

            print(f"[DEBUG] Successfully processed all chunks for task {deal.id}")
        return True, deal.id
    except Exception as e:
        print(f"[ERROR] Failed to process deal task {deal.id}")
        print(f"[ERROR] Error details: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False, deal.id


async def process_deals(
    deal_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Process multiple deals asynchronously."""
    manager = None
    successful_deals = []
    failed_deals = []

    try:
        print(f"[DEBUG] Starting to process deals: {deal_ids}")
        # Get deals from database
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        results = await session.exec(statement)
        deals = results.all()
        print(f"[DEBUG] Found {len(deals)} deals to process")

        # Update status to processing for all deals
        for deal in deals:
            deal.status = DealStatus.PROCESSING
        await session.commit()
        print("[DEBUG] Updated all deals status to PROCESSING")

        # Get direct manager instance
        print("[DEBUG] Connecting to MT5 manager")
        manager = get_mt5_manager()
        print("[DEBUG] Successfully connected to MT5 manager")

        # Get account groups
        print("[DEBUG] Fetching account groups")
        total_accounts_group = manager.UserGetByGroup("demo\\Nostro\\*")
        account_numbers = [account.Login for account in total_accounts_group]
        print(f"[DEBUG] Found {len(account_numbers)} accounts")

        # Create tasks for all deals with the same account numbers and manager
        print("[DEBUG] Creating processing tasks")
        tasks = [
            process_single_deal(deal, account_numbers, manager, session)
            for deal in deals
        ]

        # Run all tasks concurrently
        print("[DEBUG] Starting concurrent processing of all tasks")
        results = await asyncio.gather(*tasks)
        print("[DEBUG] Completed processing all tasks")

        # Process results and update statuses
        for success, deal_id in results:
            if success:
                successful_deals.append(deal_id)
                print(f"[DEBUG] Deal {deal_id} processed successfully")
            else:
                failed_deals.append(deal_id)
                print(f"[DEBUG] Deal {deal_id} processing failed")

        # Update statuses in database
        print("[DEBUG] Updating final statuses in database")
        statement = select(DealTask).where(DealTask.id.in_(successful_deals))
        results = await session.exec(statement)
        success_deals = results.all()

        for deal in success_deals:
            deal.status = DealStatus.SUCCESS

        statement = select(DealTask).where(DealTask.id.in_(failed_deals))
        results = await session.exec(statement)
        failed_deals_db = results.all()

        for deal in failed_deals_db:
            deal.status = DealStatus.FAILED

        await session.commit()
        print("[DEBUG] Successfully updated all deal statuses")

        return len(failed_deals) == 0, successful_deals, failed_deals

    except Exception as e:
        print(f"[ERROR] Error in process_deals: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

        # Update all deals to failed status in case of unexpected error
        print("[DEBUG] Updating all deals to FAILED status due to error")
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        results = await session.exec(statement)
        deals = results.all()

        for deal in deals:
            deal.status = DealStatus.FAILED
        await session.commit()
        print("[DEBUG] Successfully marked all deals as FAILED")

        return False, [], deal_ids
    finally:
        if manager:
            print("[DEBUG] Disconnecting from MT5 manager")
            manager.Disconnect()
            print("[DEBUG] Successfully disconnected from MT5 manager")
