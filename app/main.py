from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, StreamingResponse
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

import os


if not os.path.exists("app/static"):
    os.makedirs("app/static")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_hack():
    return {}

@app.get("/")
def read_root(request: Request, db: Session = Depends(database.get_db)):
    projects = crud.get_projects(db)
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})

from fastapi.responses import FileResponse
import os

@app.get("/template")
def download_template():
    file_path = "./TOR_template.xlsx"
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="TOR_Template.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return {"error": "Template file not found"}

@app.post("/projects/")
def create_project(
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(database.get_db)
):
    project_data = schemas.ProjectCreate(name=name, description=description)
    crud.create_project(db, project_data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/projects/{project_id}/dashboard")
def read_dashboard(request: Request, project_id: int, db: Session = Depends(database.get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    items = crud.get_tor_items(db, project_id=project_id, limit=1000)
    return templates.TemplateResponse("index.html", {"request": request, "items": items, "project": project})

@app.get("/projects/{project_id}/add")
def add_form(request: Request, project_id: int, db: Session = Depends(database.get_db)):
    project = crud.get_project(db, project_id)
    return templates.TemplateResponse("form.html", {"request": request, "project": project})

@app.post("/projects/{project_id}/add")
async def add_item(
    request: Request,
    project_id: int,
    task_id: str = Form(...),
    task_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    responsible: str = Form(None),
    progress: float = Form(0.0),
    db: Session = Depends(database.get_db)
):
    item_data = schemas.TORItemCreate(
        project_id=project_id,
        task_id=task_id,
        task_name=task_name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
        responsible=responsible,
        progress=progress
    )
    crud.create_tor_item(db, item_data)
    return RedirectResponse(url=f"/projects/{project_id}/dashboard", status_code=303)

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
    # Fetch existing item to get project_id
    existing_item = crud.get_tor_item(db, item_id)
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_data = schemas.TORItemCreate(
        project_id=existing_item.project_id, # Use existing project_id
        task_id=task_id,
        task_name=task_name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
        responsible=responsible,
        progress=progress
    )
    crud.update_tor_item(db, item_id, item_data)
    
    return RedirectResponse(url=f"/projects/{existing_item.project_id}/dashboard", status_code=303)

@app.post("/projects/{project_id}/upload/")
async def upload_excel(project_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    contents = await file.read()
    try:
        # Read with header=2 (Row 3 in Excel) as per Redesign.xlsx structure
        df = pd.read_excel(io.BytesIO(contents), header=2)
        
        # Clear existing data for this file AND project
        crud.delete_items_by_source(db, project_id, file.filename)
        
        for index, row in df.iterrows():
            # ... (mapping logic unchanged) ...
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
                project_id=project_id,
                task_id=str(task_id),
                task_name=str(task_name),
                start_date=start_date,
                end_date=end_date,
                responsible=str(row.get('Unnamed: 6')) if not pd.isna(row.get('Unnamed: 6')) else None,
                progress=float(row.get('Unnamed: 5', 0)) if not pd.isna(row.get('Unnamed: 5')) else 0.0,
                source_file=file.filename
            )
            crud.create_tor_item(db, item_data)
            
        return {"message": "File processed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/projects/{project_id}/analytics")
def read_analytics(request: Request, project_id: int, db: Session = Depends(database.get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    items = crud.get_tor_items(db, project_id=project_id, limit=10000)
    
    total_tasks = len(items)
    if total_tasks > 0:
        avg_progress = sum(item.progress for item in items) / total_tasks
    else:
        avg_progress = 0
        
    today = datetime.now().date()
    # Overdue: End date passed AND progress < 100
    overdue_tasks = sum(1 for item in items if item.end_date and item.end_date < today and item.progress < 100)
    completed_tasks = sum(1 for item in items if item.progress == 100)
    
    # Chart Data Preparation
    status_counts = {
        "not_started": sum(1 for item in items if item.progress == 0),
        "in_progress": sum(1 for item in items if 0 < item.progress < 100),
        "completed": completed_tasks
    }
    
    responsible_counts = {}
    for item in items:
        resp = item.responsible or "Unassigned"
        # Split multiple responsible logic if needed? Assuming single string for now or taking first part
        # Let's keep it simple grouped by the exact string
        responsible_counts[resp] = responsible_counts.get(resp, 0) + 1
        
    # Sort responsible by count desc and take top 10 to avoid overcrowding
    responsible_counts = dict(sorted(responsible_counts.items(), key=lambda item: item[1], reverse=True)[:10])

    stats = {
        "total_tasks": total_tasks,
        "avg_progress": round(avg_progress, 1),
        "overdue_tasks": overdue_tasks,
        "completed_tasks": completed_tasks
    }
    
    chart_data = {
        "status": status_counts,
        "responsible": responsible_counts
    }

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "project": project,
        "stats": stats,
        "chart_data": chart_data
    })

@app.get("/projects/{project_id}/export")
def export_project_excel(project_id: int, db: Session = Depends(database.get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    items = crud.get_tor_items(db, project_id=project_id, limit=10000)
    
    # Convert to DataFrame
    data = []
    for item in items:
        data.append({
            "Task ID": item.task_id,
            "Task Name": item.task_name,
            "Start Date": item.start_date,
            "End Date": item.end_date,
            "Progress": item.progress,
            "Responsible": item.responsible,
            "Source File": item.source_file
        })
    
    df = pd.DataFrame(data)
    
    # Create BytesIO buffer
    output = io.BytesIO()
    
    # Write to Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TOR Items')
        
    output.seek(0)
    
    filename = f"{project.name}_TOR_Export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.delete("/projects/{project_id}/delete_source/{source_file}")
def delete_source(project_id: int, source_file: str, db: Session = Depends(database.get_db)):
    crud.delete_items_by_source(db, project_id, source_file)
    return {"message": f"Data from {source_file} deleted"}

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(database.get_db)):
    item = crud.delete_tor_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}
