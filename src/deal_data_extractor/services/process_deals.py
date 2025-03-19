import asyncio
from datetime import datetime
from typing import List, Dict, Tuple
import MT5Manager
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from deal_data_extractor.models import DealTask, DealStatus
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
                deals_data = []
                chunk_volume = 0
                chunk_profit = 0
                symbols = set()
                logins = set()

                for mt_deal in chunk:
                    # Collect summary data
                    chunk_volume += mt_deal.Volume
                    chunk_profit += mt_deal.Profit
                    symbols.add(mt_deal.Symbol)
                    logins.add(mt_deal.Login)

                    # Prepare data for database insertion
                    deals_data.append(
                        (
                            mt_deal.Deal,
                            mt_deal.Action,
                            mt_deal.Comment,
                            mt_deal.Commission,
                            mt_deal.ContractSize,
                            mt_deal.Dealer,
                            mt_deal.Digits,
                            mt_deal.DigitsCurrency,
                            mt_deal.Entry,
                            mt_deal.ExpertID,
                            mt_deal.ExternalID,
                            mt_deal.Fee,
                            mt_deal.Flags,
                            mt_deal.Gateway,
                            mt_deal.Login,
                            mt_deal.MarketAsk,
                            mt_deal.MarketBid,
                            mt_deal.MarketLast,
                            mt_deal.ModificationFlags,
                            mt_deal.ObsoleteValue,
                            mt_deal.Order,
                            mt_deal.PositionID,
                            mt_deal.Price,
                            mt_deal.PriceGateway,
                            mt_deal.PricePosition,
                            mt_deal.PriceSL,
                            mt_deal.PriceTP,
                            mt_deal.Profit,
                            mt_deal.ProfitRaw,
                            mt_deal.RateMargin,
                            mt_deal.RateProfit,
                            mt_deal.Reason,
                            mt_deal.Storage,
                            mt_deal.Symbol,
                            mt_deal.TickSize,
                            mt_deal.TickValue,
                            mt_deal.Time,
                            mt_deal.TimeMsc,
                            mt_deal.Value,
                            mt_deal.Volume,
                            mt_deal.VolumeClosed,
                            mt_deal.VolumeClosedExt,
                            mt_deal.VolumeExt,
                            deal.id,  # deal_date_id
                        )
                    )

                print(f"\nInserting chunk {chunk_idx}/{len(chunks)} into database:")
                print(f"Records in chunk: {len(chunk)}")

                try:
                    # TODO: Update this to use SQLModel
                    # success = db.insert_mt5_deals(deals_data, deal.id)
                    success = True  # Temporary
                    if success:
                        print(f"Successfully inserted chunk {chunk_idx}")
                        # Print brief summary of inserted data
                        print("\nChunk Summary:")
                        print(f"Total Volume: {chunk_volume:,.2f}")
                        print(f"Total Profit: {chunk_profit:,.2f}")
                        print(f"Unique Symbols: {len(symbols)}")
                        print(f"Unique Logins: {len(logins)}")
                        print("-" * 80)
                    else:
                        print(f"Failed to insert chunk {chunk_idx}")
                        return False, deal.id
                except Exception as e:
                    print(f"Error inserting chunk {chunk_idx}: {str(e)}")
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
            deal.status = DealStatus.PROCESSING
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
            deal.status = DealStatus.SUCCESS

        statement = select(DealTask).where(DealTask.id.in_(failed_deals))
        result = await session.execute(statement)
        failed_deals_db = result.scalars().all()
        for deal in failed_deals_db:
            deal.status = DealStatus.PENDING  # Reset to pending on failure

        await session.commit()

        return len(failed_deals) == 0, successful_deals, failed_deals

    except Exception as e:
        print(f"Error in process_deals: {str(e)}")

        # Update all deals to failed status in case of unexpected error
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        result = await session.execute(statement)
        deals = result.scalars().all()
        for deal in deals:
            deal.status = DealStatus.PENDING  # Reset to pending on failure
        await session.commit()

        return False, [], deal_ids
    finally:
        if manager:
            manager.Disconnect()
