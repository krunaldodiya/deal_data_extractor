import traceback
import asyncio

from typing import List, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from models import DealTask, MT5Deal


async def delete_task(task_id: int, session: AsyncSession) -> bool:
    """Delete a task by first deleting its associated deals using raw SQL"""
    try:
        # Get the task
        statement = select(DealTask).where(DealTask.id == task_id)
        results = await session.exec(statement)
        task = results.one_or_none()

        if not task:
            print(f"Task {task_id} not found")
            return False

        print(f"Deleting deals for task {task_id} using raw SQL")

        # Use raw SQL to delete the deals first
        delete_deals_sql = text(f"DELETE FROM deals WHERE deal_task_id = {task_id}")
        await session.execute(delete_deals_sql)

        # Now delete the task
        print(f"Deleting task {task_id}")
        await session.delete(task)
        await session.commit()
        print(f"Task {task_id} deleted successfully")
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
