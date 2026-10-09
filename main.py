"""TaskFlow API: FastAPI + Supabase (Postgres)."""
import os
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY (see backend/.env.example).")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="TaskFlow API", version="1.0.0")

origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

Priority = Literal["high", "medium", "low"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: Priority = "medium"
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    done: Optional[bool] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None


def _db_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Database error: {exc}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks(status: Literal["all", "open", "done"] = Query("all")):
    try:
        q = supabase.table("tasks").select("*").order("created_at", desc=True)
        if status == "open":
            q = q.eq("done", False)
        elif status == "done":
            q = q.eq("done", True)
        return q.execute().data
    except Exception as exc:
        raise _db_error(exc)


@app.post("/tasks", status_code=201)
def create_task(body: TaskCreate):
    payload = body.model_dump(mode="json")
    payload["title"] = payload["title"].strip()
    if not payload["title"]:
        raise HTTPException(status_code=422, detail="Title cannot be empty.")
    try:
        res = supabase.table("tasks").insert(payload).execute()
        return res.data[0]
    except Exception as exc:
        raise _db_error(exc)


@app.patch("/tasks/{task_id}")
def update_task(task_id: UUID, body: TaskUpdate):
    changes = body.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update.")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        if not changes["title"]:
            raise HTTPException(status_code=422, detail="Title cannot be empty.")
    try:
        res = supabase.table("tasks").update(changes).eq("id", str(task_id)).execute()
    except Exception as exc:
        raise _db_error(exc)
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    return res.data[0]


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: UUID):
    try:
        res = supabase.table("tasks").delete().eq("id", str(task_id)).execute()
    except Exception as exc:
        raise _db_error(exc)
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found.")
