import asyncio
import MT5Manager

from typing import List, Dict
from libs.manager import get_mt5_manager
from database import Database

db = Database()


async def process_single_deal(deal: Dict, account_numbers: List[str], manager):
    try:
        # Use the deal's start and end datetime with pre-fetched account numbers
        deals = manager.DealRequestByLogins(
            account_numbers, deal["start_datetime"], deal["end_datetime"]
        )

        if not deals:
            print(MT5Manager.LastError())
            exit()

        print("deals", deals)
        print(f"Processing Deal {deal['id']}:")
        print(f"  Start: {deal['start_datetime']}")
        print(f"  End: {deal['end_datetime']}")
        print(f"  Status: {deal['status']}")
        print("---")

        return True, deal["id"]  # Return both success status and deal ID
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


# Helper function to run the async function
def process_deals_sync(deals: List[Dict]):
    return asyncio.run(process_deals(deals))
