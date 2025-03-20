import traceback
import asyncio

from typing import List, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from models import DealTask, MT5Deal


async def delete_task(task_id: int, session: AsyncSession) -> bool:
    """Delete a task and properly handle associated deals"""
    try:
        # Get the task
        statement = select(DealTask).where(DealTask.id == task_id)
        results = await session.exec(statement)
        task = results.one_or_none()

        if not task:
            print(f"Task {task_id} not found")
            return False

        # Instead of setting deal_task_id to NULL, we need to delete the associated deals first
        # since the 'deal_task_id' column has a NOT NULL constraint
        deals_statement = select(MT5Deal).where(MT5Deal.deal_task_id == task_id)
        deals_results = await session.exec(deals_statement)
        deals = deals_results.all()

        # Delete all deals associated with this task
        for deal in deals:
            await session.delete(deal)

        # Now delete the task
        await session.delete(task)
        await session.commit()
        return True

    except Exception as e:
        print(f"Error deleting task {task_id}: {str(e)}")
        print(traceback.format_exc())
        await session.rollback()
        return False


async def delete_tasks(
    task_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Delete multiple tasks (no longer deletes associated deals)."""
    successful_deletes = []
    failed_deletes = []

    try:
        # Create tasks for all task deletions
        tasks = [delete_task(task_id, session) for task_id in task_ids]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            task_id = task_ids[i]
            if isinstance(result, Exception):
                print(f"Exception in delete_tasks for task {task_id}: {str(result)}")
                failed_deletes.append(task_id)
            elif result:
                successful_deletes.append(task_id)
            else:
                failed_deletes.append(task_id)

        return len(failed_deletes) == 0, successful_deletes, failed_deletes

    except Exception as e:
        print(f"Error in delete_tasks: {str(e)}")
        print(traceback.format_exc())
        return False, [], task_ids
