import asyncio
from datetime import datetime
from typing import List, Dict, Tuple
import MT5Manager
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from deal_data_extractor.models import DealTask, DealStatus, MT5Deal
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
    deal: DealTask, account_numbers: List[str], manager, session: AsyncSession
):
    try:
        # Convert deal date and times to datetime objects
        start_datetime = datetime.combine(deal.date, deal.start_time)
        end_datetime = datetime.combine(deal.date, deal.end_time)

        # Use the deal's start and end datetime with pre-fetched account numbers
        mt_deals = manager.DealRequestByLogins(
            account_numbers, start_datetime, end_datetime
        )

        if not mt_deals:
            print(MT5Manager.LastError())
            return False, deal.id

        total_deals = len(mt_deals)
        print(f"\nTotal deals found: {total_deals}")

        if total_deals > 0:
            # Process in chunks of 1000 deals
            CHUNK_SIZE = 1000
            chunks = chunk_list(mt_deals, CHUNK_SIZE)

            print(f"\nProcessing Deal {deal.id}:")
            print(f"Start: {start_datetime}")
            print(f"End: {end_datetime}")
            print(f"Status: {deal.status}")
            print(f"Processing {len(chunks)} chunks of data...")

            # Process and insert each chunk
            for chunk_idx, chunk in enumerate(chunks, 1):
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

                print(f"\nInserting chunk {chunk_idx}/{len(chunks)} into database:")
                print(f"Records in chunk: {len(chunk)}")

                try:
                    # Insert all deals in the chunk
                    session.add_all(mt5_deals_to_insert)
                    await session.commit()

                    print(f"Successfully inserted chunk {chunk_idx}")
                    # Print brief summary of inserted data
                    print("\nChunk Summary:")
                    print(f"Total Volume: {chunk_volume:,.2f}")
                    print(f"Total Profit: {chunk_profit:,.2f}")
                    print(f"Unique Symbols: {len(symbols)}")
                    print(f"Unique Logins: {len(logins)}")
                    print("-" * 80)
                except Exception as e:
                    print(f"Error inserting chunk {chunk_idx}: {str(e)}")
                    await session.rollback()
                    return False, deal.id

        return True, deal.id
    except Exception as e:
        print(f"Error processing deal {deal.id}: {str(e)}")
        return False, deal.id


async def process_deals(
    deal_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Process multiple deals asynchronously."""
    manager = None
    successful_deals = []
    failed_deals = []

    try:
        # Get deals from database
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        result = await session.execute(statement)
        deals = result.scalars().all()

        # Update status to processing for all deals
        for deal in deals:
            deal.status = "PROCESSING"
        await session.commit()

        # Get direct manager instance
        manager = get_mt5_manager()

        # Get account groups
        total_accounts_group = manager.UserGetByGroup("demo\\Nostro\\*")
        account_numbers = [account.Login for account in total_accounts_group]

        # Create tasks for all deals with the same account numbers and manager
        tasks = [
            process_single_deal(deal, account_numbers, manager, session)
            for deal in deals
        ]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Process results and update statuses
        for success, deal_id in results:
            if success:
                successful_deals.append(deal_id)
            else:
                failed_deals.append(deal_id)

        # Update statuses in database
        statement = select(DealTask).where(DealTask.id.in_(successful_deals))
        result = await session.execute(statement)
        success_deals = result.scalars().all()
        for deal in success_deals:
            deal.status = "SUCCESS"

        statement = select(DealTask).where(DealTask.id.in_(failed_deals))
        result = await session.execute(statement)
        failed_deals_db = result.scalars().all()
        for deal in failed_deals_db:
            deal.status = "FAILED"

        await session.commit()

        return len(failed_deals) == 0, successful_deals, failed_deals

    except Exception as e:
        print(f"Error in process_deals: {str(e)}")

        # Update all deals to failed status in case of unexpected error
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        result = await session.execute(statement)
        deals = result.scalars().all()
        for deal in deals:
            deal.status = "FAILED"
        await session.commit()

        return False, [], deal_ids
    finally:
        if manager:
            manager.Disconnect()
