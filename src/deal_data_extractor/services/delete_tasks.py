from typing import List, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text

from deal_data_extractor.models import DealTask, MT5Deal


async def delete_tasks(
    deal_ids: List[int], session: AsyncSession
) -> Tuple[bool, List[int], List[int]]:
    """Delete multiple tasks asynchronously.

    Args:
        deal_ids: List of task IDs to delete
        session: Database session

    Returns:
        Tuple containing:
        - bool: True if all tasks were deleted successfully
        - List[int]: Successfully deleted task IDs
        - List[int]: Failed task IDs
    """
    successful_deletes = []
    failed_deletes = []

    try:
        # Get tasks to delete
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        result = await session.execute(statement)
        tasks = result.scalars().all()

        # Delete each task and its associated MT5 deals
        for task in tasks:
            try:
                # First delete associated MT5 deals using raw SQL
                delete_deals_sql = text(
                    "DELETE FROM deals WHERE deal_task_id = :task_id"
                )
                await session.execute(delete_deals_sql, {"task_id": task.id})

                # Then delete the task
                await session.delete(task)
                successful_deletes.append(task.id)
            except Exception as e:
                print(f"Failed to delete task {task.id}: {str(e)}")
                failed_deletes.append(task.id)
                await session.rollback()
                continue

        # Commit the changes
        await session.commit()

        return len(failed_deletes) == 0, successful_deletes, failed_deletes

    except Exception as e:
        print(f"Error in delete_tasks: {str(e)}")
        await session.rollback()
        # If there's an error, consider all deletions failed
        return False, [], deal_ids
