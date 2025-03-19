import asyncio
import MT5Manager
from typing import List, Dict, Tuple
from libs.manager import get_mt5_manager
from database import Database
import streamlit as st

db = Database()

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


async def process_single_deal(deal: Dict, account_numbers: List[str], manager):
    try:
        # Use the deal's start and end datetime with pre-fetched account numbers
        mt_deals = manager.DealRequestByLogins(
            account_numbers, deal["start_datetime"], deal["end_datetime"]
        )

        if not mt_deals:
            print(MT5Manager.LastError())
            return False, deal["id"]

        total_deals = len(mt_deals)
        print(f"\nTotal deals found: {total_deals}")

        if total_deals > 0:
            # Process in chunks of 1000 deals
            CHUNK_SIZE = 1000
            chunks = chunk_list(mt_deals, CHUNK_SIZE)

            print(f"\nProcessing Deal {deal['id']}:")
            print(f"Start: {deal['start_datetime']}")
            print(f"End: {deal['end_datetime']}")
            print(f"Status: {deal['status']}")
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
                            deal["id"],  # deal_date_id
                        )
                    )

                print(f"\nInserting chunk {chunk_idx}/{len(chunks)} into database:")
                print(f"Records in chunk: {len(chunk)}")

                try:
                    success = db.insert_mt5_deals(deals_data, deal["id"])
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
                        return False, deal["id"]
                except Exception as e:
                    print(f"Error inserting chunk {chunk_idx}: {str(e)}")
                    return False, deal["id"]

        return True, deal["id"]
    except Exception as e:
        print(f"Error processing deal {deal['id']}: {str(e)}")
        return False, deal["id"]


async def process_deals(deals: List[Dict]):
    manager = None

    try:
        # Update status to processing for all deals
        for deal in deals:
            db.update_deal_status(deal["id"], "processing")

        # Get direct manager instance
        manager = get_mt5_manager()

        # Get account groups
        total_accounts_group = manager.UserGetByGroup("demo\\Nostro\\*")
        account_numbers = [account.Login for account in total_accounts_group]

        # Create tasks for all deals with the same account numbers and manager
        tasks = [process_single_deal(deal, account_numbers, manager) for deal in deals]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Process results and update statuses
        successful_deals = []
        failed_deals = []

        for success, deal_id in results:
            if success:
                successful_deals.append(deal_id)
            else:
                failed_deals.append(deal_id)

        # Update statuses in database
        for deal_id in successful_deals:
            db.update_deal_status(deal_id, "success")

        for deal_id in failed_deals:
            db.update_deal_status(deal_id, "failed")

        # Return True only if all deals were successful
        return len(successful_deals) == len(deals)

    except Exception as e:
        print(f"Error in process_deals: {str(e)}")

        # Update all deals to failed status in case of unexpected error
        for deal in deals:
            db.update_deal_status(deal["id"], "failed")

        return False
    finally:
        if manager:
            manager.Disconnect()


def process_deals_sync(deals: List[Dict]) -> Tuple[bool, List[int], List[int]]:
    """
    Process multiple deals synchronously.

    Args:
        deals: List of deal dictionaries containing id, start_datetime, end_datetime, and status

    Returns:
        Tuple containing:
        - bool: True if all deals were processed successfully
        - List[int]: Successfully processed deal IDs
        - List[int]: Failed deal IDs
    """
    try:
        # Run the async function using asyncio
        success = asyncio.run(process_deals(deals))

        # Get the final status of all deals from the database
        success_ids = []
        failed_ids = []

        for deal in deals:
            status = db.get_deal_status(deal["id"])
            if status == "success":
                success_ids.append(deal["id"])
            else:
                failed_ids.append(deal["id"])

        return len(failed_ids) == 0, success_ids, failed_ids
    except Exception as e:
        print(f"Error in process_deals_sync: {str(e)}")
        return False, [], [d["id"] for d in deals]
