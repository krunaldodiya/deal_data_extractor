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
        # Create the task using the service
        await create_task(date, start_time, end_time, session)

        # Get updated list of tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        tasks = result.scalars().all()

        # Return just the tasks table portion
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
                "error": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process")
async def process_deals(
    request: Request,
    deal_ids: List[int] = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Process selected deals."""
    try:
        # Update status to processing for selected deals
        statement = select(DealTask).where(DealTask.id.in_(deal_ids))
        result = await session.execute(statement)
        tasks = result.scalars().all()

        for task in tasks:
            task.status = DealStatus.PROCESSING

        await session.commit()

        # Get updated list of all tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        all_tasks = result.scalars().all()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "deal_tasks": all_tasks,
                "message": f"Processing {len(deal_ids)} deals",
                "today": datetime.now().date(),
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
        success, successful_deletes, failed_deletes = await delete_tasks(
            selected_tasks, session
        )

        # Get updated list of all tasks
        statement = select(DealTask).order_by(
            DealTask.date.desc(), DealTask.start_time.desc()
        )
        result = await session.execute(statement)
        remaining_tasks = result.scalars().all()

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
        raise HTTPException(status_code=400, detail=str(e))
