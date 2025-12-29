from sqlalchemy.orm import Session
from . import models, schemas
from datetime import date
from dateutil.relativedelta import relativedelta

def get_tor_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.TORItem).offset(skip).limit(limit).all()

def create_tor_item(db: Session, tor_item: schemas.TORItemCreate):
    # Calculate warranty end date (3 years from end_date)
    warranty_end_date = tor_item.end_date + relativedelta(years=3)
    
    db_item = models.TORItem(
        task_id=tor_item.task_id,
        task_name=tor_item.task_name,
        start_date=tor_item.start_date,
        end_date=tor_item.end_date,
        warranty_end_date=warranty_end_date,
        responsible=tor_item.responsible,
        progress=tor_item.progress
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
        
        # Recalculate warranty
        db_item.warranty_end_date = tor_item.end_date + relativedelta(years=3)
        
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_all_tor_items(db: Session):
    db.query(models.TORItem).delete()
    db.commit()
