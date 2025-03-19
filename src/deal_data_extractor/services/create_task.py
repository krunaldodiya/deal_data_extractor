from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError

from deal_data_extractor.models import DealTask, DealStatus


async def create_task(
    date: str,
    start_time: str,
    end_time: str,
    session: AsyncSession,
) -> DealTask:
    """Create a new deal task.

    Args:
        date: Date in YYYY-MM-DD format
        start_time: Time in HH:MM format
        end_time: Time in HH:MM format
        session: Database session

    Returns:
        The created DealTask instance

    Raises:
        ValueError: If date or time formats are invalid or if task already exists
    """
    try:
        # Parse the date and times
        task_date = datetime.strptime(date, "%Y-%m-%d").date()
        task_start_time = datetime.strptime(start_time, "%H:%M").time()
        task_end_time = datetime.strptime(end_time, "%H:%M").time()

        # Validate times
        if task_start_time >= task_end_time:
            raise ValueError("End time must be after start time")

        # Create new task
        task = DealTask(
            date=task_date,
            start_time=task_start_time,
            end_time=task_end_time,
            status="PENDING",
        )

        session.add(task)
        try:
            await session.commit()
            await session.refresh(task)
            return task
        except IntegrityError:
            await session.rollback()
            raise ValueError("A task with these date and time values already exists")

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise Exception(f"Failed to create task: {str(e)}")
