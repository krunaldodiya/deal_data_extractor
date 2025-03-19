from typing import List, Tuple
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import traceback

from deal_data_extractor.models import DealTask, MT5Deal


async def delete_task_with_deals(task_id: int, session: AsyncSession) -> bool:
    """Delete a task and all its associated MT5 deals"""
    try:
        # First, select all the deals associated with this task
        statement = select(MT5Deal).where(MT5Deal.deal_task_id == task_id)
        result = await session.execute(statement)
        deals = result.scalars().all()

        # Delete the deals
        for deal in deals:
            await session.delete(deal)

        # Then, get and delete the task
        statement = select(DealTask).where(DealTask.id == task_id)
        result = await session.execute(statement)
        task = result.scalar_one_or_none()

        if task:
            await session.delete(task)
            await session.commit()
            return True
        else:
            print(f"Task {task_id} not found")
            return False
    except Exception as e:
        print(f"Error deleting task {task_id}: {str(e)}")
        print(traceback.format_exc())
        await session.rollback()
        return False


async def delete_tasks(
    task_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Delete multiple tasks and their associated deals."""
    successful_deletes = []
    failed_deletes = []

    try:
        # Create tasks for all task deletions
        tasks = [delete_task_with_deals(task_id, session) for task_id in task_ids]

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
