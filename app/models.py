from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from .database import Base

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    created_at = Column(Date, default=datetime.utcnow)

    items = relationship("TORItem", back_populates="project")

class TORItem(Base):
    __tablename__ = "tor_items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    task_id = Column(String, index=True)
    task_name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    responsible = Column(String)
    delivery_term = Column(String, nullable=True)
    progress = Column(Float, default=0.0)
    email_sent = Column(Boolean, default=False)
    source_file = Column(String, default="Manual Input")

    project = relationship("Project", back_populates="items")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
