import traceback
import asyncio

from typing import List, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from models import DealTask, MT5Deal


async def delete_task(task_id: int, session: AsyncSession) -> bool:
    """Delete a task by first deleting its associated deals using SQLModel in batches"""
    try:
        # Get the task
        statement = select(DealTask).where(DealTask.id == task_id)
        results = await session.exec(statement)
        task = results.one_or_none()

        if not task:
            print(f"Task {task_id} not found")
            return False

        print(f"Deleting deals for task {task_id} in batches")

        # Delete deals in batches to handle large numbers efficiently
        batch_size = 1000
        total_deleted = 0

        while True:
            # Get a batch of deals
            deals_statement = (
                select(MT5Deal).where(MT5Deal.deal_task_id == task_id).limit(batch_size)
            )
            deals_results = await session.exec(deals_statement)
            deals_batch = deals_results.all()

            if not deals_batch:
                break  # No more deals to delete

            batch_count = len(deals_batch)
            print(f"Deleting batch of {batch_count} deals for task {task_id}")

            # Delete the deals in this batch
            for deal in deals_batch:
                await session.delete(deal)

            await session.flush()
            total_deleted += batch_count
            print(f"Deleted {total_deleted} deals so far for task {task_id}")

        # Now delete the task
        print(f"Deleting task {task_id}")
        await session.delete(task)
        await session.commit()
        print(
            f"Task {task_id} deleted successfully after removing {total_deleted} deals"
        )
        return True

    except Exception as e:
        print(f"Error deleting task {task_id}: {str(e)}")
        print(traceback.format_exc())
        await session.rollback()
        return False


async def delete_tasks(
    task_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Delete multiple tasks sequentially to avoid concurrency issues."""
    successful_deletes = []
    failed_deletes = []

    try:
        # Process tasks sequentially to avoid concurrency issues
        for task_id in task_ids:
            try:
                result = await delete_task(task_id, session)
                if result:
                    successful_deletes.append(task_id)
                else:
                    failed_deletes.append(task_id)

                # Add a short delay between deletions
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Exception in delete_tasks for task {task_id}: {str(e)}")
                failed_deletes.append(task_id)

        return len(failed_deletes) == 0, successful_deletes, failed_deletes

    except Exception as e:
        print(f"Error in delete_tasks: {str(e)}")
        print(traceback.format_exc())
        return False, [], task_ids
