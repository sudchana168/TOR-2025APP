from pydantic import BaseModel
from datetime import date
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: date

    class Config:
        from_attributes = True

class TORItemBase(BaseModel):
    task_id: str
    task_name: str
    start_date: date
    end_date: date
    responsible: Optional[str] = None
    delivery_term: Optional[str] = None
    progress: Optional[float] = 0.0

class TORItemCreate(TORItemBase):
    source_file: Optional[str] = "Manual Input"
    project_id: int

class TORItem(TORItemBase):
    id: int
    project_id: int
    email_sent: bool
    source_file: str

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
