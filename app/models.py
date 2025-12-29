from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from .database import Base

class TORItem(Base):
    __tablename__ = "tor_items"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True)
    task_name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    warranty_end_date = Column(Date)
    responsible = Column(String)
    progress = Column(Float, default=0.0)
    email_sent = Column(Boolean, default=False)
