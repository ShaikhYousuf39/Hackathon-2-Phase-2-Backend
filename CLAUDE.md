# Backend Development Guide

## Overview
FastAPI application with SQLModel ORM for PostgreSQL database.

## Stack
- **Framework**: FastAPI
- **Language**: Python 3.13+
- **ORM**: SQLModel
- **Database**: PostgreSQL (Neon Serverless)
- **Auth**: JWT verification
- **Validation**: Pydantic

## Project Structure
```
backend/
├── main.py                 # FastAPI app entry point
├── models.py              # SQLModel database models
├── schemas.py             # Pydantic request/response schemas
├── database.py            # Database connection
├── middleware/
│   └── auth.py           # JWT verification middleware
├── routes/
│   └── tasks.py          # Task endpoints
├── utils/
│   └── jwt.py            # JWT utilities
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── alembic/              # Database migrations (future)
└── CLAUDE.md             # This file
```

## Development Guidelines

### 1. FastAPI Application Setup

#### main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import tasks
import os

app = FastAPI(
    title="Todo API",
    description="RESTful API for Todo application",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router, prefix="/api", tags=["tasks"])

@app.get("/")
def read_root():
    return {"message": "Todo API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### 2. Database Models

#### models.py
```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    password: str
    email_verified: bool = Field(default=False)
    image: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = None
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. Request/Response Schemas

#### schemas.py
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class TaskResponse(BaseModel):
    id: int
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
```

### 4. Database Connection

#### database.py
```python
from sqlmodel import create_engine, SQLModel, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    """Create all tables in the database"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session
```

### 5. JWT Verification

#### utils/jwt.py
```python
import jwt
import os
from datetime import datetime
from typing import Optional

SECRET_KEY = os.getenv("BETTER_AUTH_SECRET")

if not SECRET_KEY:
    raise ValueError("BETTER_AUTH_SECRET environment variable is not set")

def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None

        return payload
    except jwt.InvalidTokenError:
        return None

def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token"""
    payload = verify_jwt(token)
    if payload:
        return payload.get("sub")  # Subject is user ID
    return None
```

#### middleware/auth.py
```python
from fastapi import Request, HTTPException, status
from utils.jwt import verify_jwt

async def verify_jwt_middleware(request: Request):
    """
    Middleware to verify JWT token in Authorization header
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format"
        )

    token = parts[1]
    payload = verify_jwt(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Attach user info to request state
    request.state.user_id = payload.get("sub")
    request.state.user_email = payload.get("email")
```

### 6. API Routes

#### routes/tasks.py
```python
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
    status: str = "all"
) -> ApiResponse:
    """Get all tasks for authenticated user"""

    # Verify user_id matches authenticated user
    if request.state.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' tasks"
        )

    # Build query
    query = select(Task).where(Task.user_id == user_id)

    if status == "pending":
        query = query.where(Task.completed == False)
    elif status == "completed":
        query = query.where(Task.completed == True)

    query = query.order_by(Task.created_at.desc())

    tasks = session.exec(query).all()

    return ApiResponse(
        success=True,
        data={"tasks": [TaskResponse.from_orm(task).dict() for task in tasks]}
    )

@router.post("/{user_id}/tasks", dependencies=[Depends(verify_jwt_middleware)], status_code=status.HTTP_201_CREATED)
async def create_task(
    user_id: str,
    task_data: TaskCreate,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """Create a new task"""

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
        data=TaskResponse.from_orm(task).dict()
    )

@router.get("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def get_task(
    user_id: str,
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """Get task details"""

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
        data=TaskResponse.from_orm(task).dict()
    )

@router.put("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def update_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """Update a task"""

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
        data=TaskResponse.from_orm(task).dict()
    )

@router.delete("/{user_id}/tasks/{task_id}", dependencies=[Depends(verify_jwt_middleware)])
async def delete_task(
    user_id: str,
    task_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> ApiResponse:
    """Delete a task"""

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
    """Toggle task completion status"""

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
        data=TaskResponse.from_orm(task).dict()
    )
```

### 7. Environment Variables

#### .env
```
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
BETTER_AUTH_SECRET=your-super-secret-key-min-32-characters
CORS_ORIGINS=http://localhost:3000
```

### 8. Dependencies

#### requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlmodel==0.0.14
psycopg2-binary==2.9.9
pyjwt==2.8.0
python-dotenv==1.0.0
pydantic==2.5.3
```

## Running the Backend

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Development Server
```bash
uvicorn main:app --reload --port 8000
```

### Run with Environment Variables
```bash
python -m uvicorn main:app --reload --port 8000
```

### API Documentation
Visit http://localhost:8000/docs for interactive API documentation (Swagger UI)

## Testing

### Manual Testing
Use the interactive docs at `/docs` to test endpoints

### Unit Tests (Future)
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

## Common Issues

### Issue: Database Connection Failed
**Solution**: Verify DATABASE_URL is correct and database is accessible

### Issue: JWT Verification Failed
**Solution**: Ensure BETTER_AUTH_SECRET matches frontend secret

### Issue: CORS Error
**Solution**: Add frontend URL to CORS_ORIGINS

## Best Practices

1. **Always Validate User ID**
   - Check JWT user_id matches URL user_id
   - Return 403 if mismatch

2. **Filter All Queries by User**
   - Every query must include `WHERE user_id = ?`
   - Never expose other users' data

3. **Validate Input**
   - Use Pydantic models for validation
   - Trim strings
   - Check length constraints

4. **Handle Errors Gracefully**
   - Return proper HTTP status codes
   - Provide clear error messages
   - Log errors for debugging

5. **Use Transactions**
   - SQLModel handles this automatically
   - Commit only on success

6. **Security**
   - Never log sensitive data
   - Hash passwords (Better Auth handles this)
   - Use HTTPS in production

## Deployment

### Using Docker
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Railway/Fly.io
1. Add Procfile: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
2. Set environment variables
3. Deploy

## References
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLModel Docs](https://sqlmodel.tiangolo.com)
- [Pydantic Docs](https://docs.pydantic.dev)
- [PyJWT Docs](https://pyjwt.readthedocs.io)
