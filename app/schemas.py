from pydantic import BaseModel
from datetime import date
from typing import Optional

class TORItemBase(BaseModel):
    task_id: str
    task_name: str
    start_date: date
    end_date: date
    responsible: Optional[str] = None
    progress: Optional[float] = 0.0

class TORItemCreate(TORItemBase):
    pass

class TORItem(TORItemBase):
    id: int
    warranty_end_date: date
    email_sent: bool

    class Config:
        from_attributes = True
