from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from typing import List
from database import get_session
from models import Task
from schemas import TaskCreate, TaskUpdate, TaskResponse, ApiResponse
from middleware.auth import verify_jwt_middleware
from datetime import datetime

router = APIRouter()


@router.get("/{user_id}/tasks", dependencies=[Depends(verify_jwt_middleware)])
async def list_tasks(
    user_id: str,
    request: Request,
    session: Session = Depends(get_session),
    filter_status: str = "all"
) -> ApiResponse:
    """
    Get all tasks for authenticated user

    Args:
        user_id: User ID from URL
        request: FastAPI request (contains authenticated user info)
        session: Database session
        filter_status: Filter by status (all, pending, completed)

    Returns:
        ApiResponse with list of tasks
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' tasks"
        )

    # Build query
    query = select(Task).where(Task.user_id == user_id)

    if filter_status == "pending":
        query = query.where(Task.completed == False)
    elif filter_status == "completed":
        query = query.where(Task.completed == True)

    query = query.order_by(Task.created_at.desc())

    tasks = session.exec(query).all()

    return ApiResponse(
        success=True,
        data=[TaskResponse.model_validate(task).model_dump() for task in tasks]
    )


@router.post(
    "/{user_id}/tasks",
    dependencies=[Depends(verify_jwt_middleware)],
    status_code=status.HTTP_201_CREATED
)
async def create_task(
    user_id: str,
    task_data: TaskCreate,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """
    Create a new task

    Args:
        user_id: User ID from URL
        task_data: Task creation data
        request: FastAPI request
        session: Database session

    Returns:
        ApiResponse with created task
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create tasks for other users"
        )

    # Create task
    task = Task(
        user_id=user_id,
        title=task_data.title.strip(),
        description=task_data.description.strip() if task_data.description else None,
        completed=False
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return ApiResponse(
        success=True,
        data=TaskResponse.model_validate(task).model_dump()
    )


@router.get("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def get_task(
    user_id: str,
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """
    Get task details

    Args:
        user_id: User ID from URL
        task_id: Task ID
        request: FastAPI request
        session: Database session

    Returns:
        ApiResponse with task details
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' tasks"
        )

    task = session.get(Task, task_id)

    if not task or task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return ApiResponse(
        success=True,
        data=TaskResponse.model_validate(task).model_dump()
    )


@router.put("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def update_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """
    Update a task

    Args:
        user_id: User ID from URL
        task_id: Task ID
        task_data: Task update data
        request: FastAPI request
        session: Database session

    Returns:
        ApiResponse with updated task
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users' tasks"
        )

    task = session.get(Task, task_id)

    if not task or task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update fields
    if task_data.title is not None:
        task.title = task_data.title.strip()
    if task_data.description is not None:
        task.description = task_data.description.strip()

    task.updated_at = datetime.utcnow()

    session.add(task)
    session.commit()
    session.refresh(task)

    return ApiResponse(
        success=True,
        data=TaskResponse.model_validate(task).model_dump()
    )


@router.delete("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def delete_task(
    user_id: str,
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """
    Delete a task

    Args:
        user_id: User ID from URL
        task_id: Task ID
        request: FastAPI request
        session: Database session

    Returns:
        ApiResponse with success message
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other users' tasks"
        )

    task = session.get(Task, task_id)

    if not task or task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    session.delete(task)
    session.commit()

    return ApiResponse(
        success=True,
        data={"message": "Task deleted successfully"}
    )


@router.patch("/{user_id}/tasks/{task_id}/complete", dependencies=[Depends(verify_jwt_middleware)])
async def toggle_task_completion(
    user_id: str,
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """
    Toggle task completion status

    Args:
        user_id: User ID from URL
        task_id: Task ID
        request: FastAPI request
        session: Database session

    Returns:
        ApiResponse with updated task
    """
    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users' tasks"
        )

    task = session.get(Task, task_id)

    if not task or task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task.completed = not task.completed
    task.updated_at = datetime.utcnow()

    session.add(task)
    session.commit()
    session.refresh(task)

    return ApiResponse(
        success=True,
        data=TaskResponse.model_validate(task).model_dump()
    )
