from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from datetime import datetime

from . import models, schemas, crud, database, scheduler

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.on_event("startup")
def start_scheduler():
    scheduler.scheduler.start()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
def read_root(request: Request, db: Session = Depends(database.get_db)):
    items = crud.get_tor_items(db, limit=1000)
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.get("/add")
def add_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/add")
async def add_item(
    request: Request,
    task_id: str = Form(...),
    task_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    responsible: str = Form(None),
    progress: float = Form(0.0),
    db: Session = Depends(database.get_db)
):
    item_data = schemas.TORItemCreate(
        task_id=task_id,
        task_name=task_name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
        responsible=responsible,
        progress=progress
    )
    crud.create_tor_item(db, item_data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/edit/{item_id}")
def edit_form(request: Request, item_id: int, db: Session = Depends(database.get_db)):
    item = crud.get_tor_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse("form.html", {"request": request, "item": item})

@app.post("/edit/{item_id}")
async def edit_item(
    request: Request,
    item_id: int,
    task_id: str = Form(...),
    task_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    responsible: str = Form(None),
    progress: float = Form(0.0),
    db: Session = Depends(database.get_db)
):
    item_data = schemas.TORItemCreate(
        task_id=task_id,
        task_name=task_name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
        responsible=responsible,
        progress=progress
    )
    crud.update_tor_item(db, item_id, item_data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/upload/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    contents = await file.read()
    try:
        # Read with header=2 (Row 3 in Excel) as per Redesign.xlsx structure
        df = pd.read_excel(io.BytesIO(contents), header=2)
        
        # Clear existing data
        crud.delete_all_tor_items(db)
        
        for index, row in df.iterrows():
            # Map columns based on inspection of Redesign.xlsx
            # Unnamed: 0 -> Task ID
            # Unnamed: 1 -> Task Name
            # Unnamed: 2 -> Start Date
            # Unnamed: 3 -> End Date
            # Unnamed: 5 -> Progress
            # Unnamed: 6 -> Responsible
            
            task_id = row.get('Unnamed: 0')
            task_name = row.get('Unnamed: 1')
            
            # Relaxed check: Only skip if BOTH are missing, or if it's clearly empty
            if pd.isna(task_id) and pd.isna(task_name):
                continue
            
            # If Task ID is missing but Name exists, use a placeholder or keep it empty
            if pd.isna(task_id):
                task_id = ""
            if pd.isna(task_name):
                task_name = "Unnamed Task"

            try:
                start_date = pd.to_datetime(row.get('Unnamed: 2'), dayfirst=True).date()
                end_date = pd.to_datetime(row.get('Unnamed: 3'), dayfirst=True).date()
            except:
                continue # Skip invalid dates

            item_data = schemas.TORItemCreate(
                task_id=str(task_id),
                task_name=str(task_name),
                start_date=start_date,
                end_date=end_date,
                responsible=str(row.get('Unnamed: 6')) if not pd.isna(row.get('Unnamed: 6')) else None,
                progress=float(row.get('Unnamed: 5', 0)) if not pd.isna(row.get('Unnamed: 5')) else 0.0
            )
            crud.create_tor_item(db, item_data)
            
        return {"message": "File processed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/items/", response_model=List[schemas.TORItem])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    items = crud.get_tor_items(db, skip=skip, limit=limit)
    return items
