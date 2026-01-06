from sqlalchemy.orm import Session
from . import models, schemas
from datetime import date


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(name=project.name, description=project.description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_tor_items(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.TORItem).filter(models.TORItem.project_id == project_id).offset(skip).limit(limit).all()

def create_tor_item(db: Session, tor_item: schemas.TORItemCreate):
    db_item = models.TORItem(
        project_id=tor_item.project_id,
        task_id=tor_item.task_id,
        task_name=tor_item.task_name,
        start_date=tor_item.start_date,
        end_date=tor_item.end_date,
        responsible=tor_item.responsible,
        progress=tor_item.progress,
        source_file=tor_item.source_file
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_tor_item(db: Session, item_id: int):
    return db.query(models.TORItem).filter(models.TORItem.id == item_id).first()

def update_tor_item(db: Session, item_id: int, tor_item: schemas.TORItemCreate):
    db_item = get_tor_item(db, item_id)
    if db_item:
        # Update fields
        db_item.task_id = tor_item.task_id
        db_item.task_name = tor_item.task_name
        db_item.start_date = tor_item.start_date
        db_item.end_date = tor_item.end_date
        db_item.responsible = tor_item.responsible
        db_item.progress = tor_item.progress
        # Note: We do NOT update source_file here to preserve origin
        
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_all_tor_items(db: Session):
    db.query(models.TORItem).delete()
    db.commit()

def delete_items_by_source(db: Session, project_id: int, source_file: str):
    db.query(models.TORItem).filter(models.TORItem.project_id == project_id, models.TORItem.source_file == source_file).delete()
    db.commit()
