from __future__ import annotations

import os
from datetime import datetime, time
from typing import List
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import pathlib

from deal_data_extractor.database import init_db, get_session
from deal_data_extractor.models import (
    DealTask,
    DealTaskCreate,
    DealTaskRead,
    DealStatus,
    ProcessDealRequest,
    DeleteDealRequest,
)
from deal_data_extractor.routes.deals import router as deals_router
from deal_data_extractor.services.process_deals import process_deals
from deal_data_extractor.services.delete_tasks import delete_tasks
from deal_data_extractor.services.create_task import create_task

app = FastAPI(title="Deal Data Extractor")

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)

# Setup templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
)

# Include deal processing routes
app.include_router(deals_router, prefix="/api/deals", tags=["deals"])


@app.on_event("startup")
async def on_startup():
    """Initialize the database on startup."""
    await init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: AsyncSession = Depends(get_session)):
    """Render the home page with deal tasks."""
    statement = select(DealTask).order_by(
        DealTask.date.desc(), DealTask.start_time.desc()
    )
    result = await session.execute(statement)
    tasks = result.scalars().all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tasks": tasks,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "DealStatus": DealStatus,
        },
    )


@app.post("/tasks", response_class=HTMLResponse)
async def create_task_endpoint(
    request: Request,
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Create a new deal task and return updated tasks list."""
    try:
        print(
            f"Creating task with date={date}, start_time={start_time}, end_time={end_time}"
        )

        # Create the task using the service
        new_task = await create_task(date, start_time, end_time, session)
        print(f"Task created successfully with id={new_task.id}")

        # Get updated list of tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        tasks = result.scalars().all()
        print(f"Retrieved {len(tasks)} tasks for response")

        # Return the updated tasks container
        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": tasks,
                "DealStatus": DealStatus,
                "message": "Task created successfully",
            },
        )
    except ValueError as e:
        print(f"ValueError in create_task: {str(e)}")
        # Return the error message with the current tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        tasks = result.scalars().all()

        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": tasks,
                "DealStatus": DealStatus,
                "message": f"Error: {str(e)}",
            },
        )
    except Exception as e:
        import traceback

        print(f"Exception in create_task: {str(e)}")
        print(traceback.format_exc())

        # Return the error response with current tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        tasks = result.scalars().all()

        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": tasks,
                "DealStatus": DealStatus,
                "message": f"Error: {str(e)}",
            },
        )


@app.post("/process")
async def process_deals_endpoint(
    request: Request,
    selected_tasks: List[int] = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Process selected deals."""
    try:
        # Call the actual processing logic
        success, successful_deals, failed_deals = await process_deals(
            selected_tasks, session
        )

        # Get updated list of all tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        all_tasks = result.scalars().all()

        # Return just the tasks table portion
        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": all_tasks,
                "DealStatus": DealStatus,
                "message": (
                    f"Successfully processed {len(successful_deals)} tasks"
                    if success
                    else f"Failed to process {len(failed_deals)} tasks"
                ),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/delete", response_class=HTMLResponse)
async def delete_deals(
    request: Request,
    selected_tasks: List[int] = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Delete selected deals."""
    try:
        print(f"Deleting tasks: {selected_tasks}")  # Debug log

        if not selected_tasks:
            print("No tasks selected for deletion")
            raise ValueError("No tasks selected for deletion")

        success, successful_deletes, failed_deletes = await delete_tasks(
            selected_tasks, session
        )

        print(
            f"Delete result: success={success}, successful_deletes={successful_deletes}, failed_deletes={failed_deletes}"
        )

        # Get updated list of all tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        remaining_tasks = result.scalars().all()

        print(f"Remaining tasks after deletion: {len(remaining_tasks)}")

        # Return just the tasks table portion
        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": remaining_tasks,
                "DealStatus": DealStatus,
                "message": (
                    f"Successfully deleted {len(successful_deletes)} tasks"
                    if success
                    else f"Failed to delete {len(failed_deletes)} tasks"
                ),
            },
        )
    except Exception as e:
        import traceback

        print(f"Error in delete_deals: {str(e)}")
        print(traceback.format_exc())  # Full stack trace

        # Return error response in the same format
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        remaining_tasks = result.scalars().all()

        return templates.TemplateResponse(
            "tasks_table.html",
            {
                "request": request,
                "tasks": remaining_tasks,
                "DealStatus": DealStatus,
                "message": f"Error: {str(e)}",
            },
            status_code=400,
        )
