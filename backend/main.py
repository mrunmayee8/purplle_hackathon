import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi.staticfiles import StaticFiles
from .database import engine, Base, get_db, SessionLocal
from .models import Event, PosTransaction, Anomaly
from .schemas import EventCreate, EventResponse, PosTransactionResponse, AnomalyResponse, SummaryKPIs, ZoneAnalytics, FunnelStage
from .pos_ingest import load_pos_transactions
from .analytics import (
    get_summary_analytics,
    get_zone_analytics,
    get_funnel_analytics,
    run_anomaly_detection,
    parse_iso_datetime,
    normalize_store_id
)
from cv_pipeline.simulate import run_simulation

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Store Intelligence API", description="AI Retail Analytics and Ingestion Engine")

# Mount Static Files for Layouts
app.mount("/Store 1", StaticFiles(directory="Store 1"), name="store1")
app.mount("/Store 2", StaticFiles(directory="Store 2"), name="store2")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Automatic POS Seeding on Startup
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        # Search for CSV file to auto-load
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Find csv files in workspace
        for file in os.listdir(root_dir):
            if "transactions" in file and file.endswith(".csv"):
                csv_path = os.path.join(root_dir, file)
                print(f"Auto-seeding database with POS CSV file: {csv_path}")
                load_pos_transactions(db, csv_path)
                break
    except Exception as e:
        print(f"Failed to auto-seed POS transactions on startup: {e}")
    finally:
        db.close()

@app.post("/api/events", status_code=201)
def ingest_event(event_data: EventCreate, db: Session = Depends(get_db)):
    """Ingests a CCTV/sensor event, validates it, and evaluates retail anomalies."""
    try:
        # Map input variations
        e_type = event_data.event_type.strip().lower()
        store = event_data.store_id or event_data.store_code or "ST1008"
        cam = event_data.camera_id
        
        # Parse timestamp from varying formats
        ts_str = event_data.event_timestamp or event_data.event_time or event_data.queue_join_ts
        ts = parse_iso_datetime(ts_str) if ts_str else datetime.utcnow()
        if not ts:
            ts = datetime.utcnow()
            
        # Standardize demographics
        gender = event_data.gender or event_data.gender_pred
        age = event_data.age or event_data.age_pred
        
        event = Event(
            event_type=e_type,
            store_id=normalize_store_id(store),
            camera_id=cam,
            timestamp=ts,
            track_id=event_data.track_id,
            id_token=event_data.id_token,
            gender=gender,
            age=age,
            age_bucket=event_data.age_bucket,
            is_staff=event_data.is_staff or False,
            is_face_hidden=event_data.is_face_hidden or False,
            group_id=event_data.group_id,
            group_size=event_data.group_size,
            zone_id=event_data.zone_id,
            zone_name=event_data.zone_name,
            zone_type=event_data.zone_type,
            is_revenue_zone=event_data.is_revenue_zone,
            zone_hotspot_x=event_data.zone_hotspot_x,
            zone_hotspot_y=event_data.zone_hotspot_y,
            queue_event_id=event_data.queue_event_id,
            queue_join_ts=parse_iso_datetime(event_data.queue_join_ts),
            queue_served_ts=parse_iso_datetime(event_data.queue_served_ts),
            queue_exit_ts=parse_iso_datetime(event_data.queue_exit_ts),
            wait_seconds=event_data.wait_seconds,
            queue_position_at_join=event_data.queue_position_at_join,
            abandoned=event_data.abandoned
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Trigger anomaly engine asynchronously or inline (small dataset is fast)
        run_anomaly_detection(db, store)
        
        return {"status": "success", "event_id": event.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to ingest event: {e}")

@app.post("/api/pos/upload")
async def upload_pos_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Manually upload and parse a POS CSV file to replace store transaction data."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    try:
        # Save temp file
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())
            
        count = load_pos_transactions(db, temp_path)
        os.remove(temp_path)
        
        return {"status": "success", "transactions_loaded": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload and load POS CSV: {e}")

@app.get("/api/analytics/summary", response_model=SummaryKPIs)
def summary_api(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Gets aggregate KPIs for a store."""
    try:
        return get_summary_analytics(db, store_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {e}")

@app.get("/api/analytics/zones", response_model=List[ZoneAnalytics])
def zone_api(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Gets visitor counts and average dwell times by zone."""
    try:
        return get_zone_analytics(db, store_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zone analytics error: {e}")

@app.get("/api/analytics/funnel", response_model=List[FunnelStage])
def funnel_api(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Gets the spatial conversion funnel stages."""
    try:
        return get_funnel_analytics(db, store_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Funnel error: {e}")

@app.get("/api/analytics/anomalies", response_model=List[AnomalyResponse])
def anomalies_api(store_id: Optional[str] = None, resolved: Optional[bool] = None, db: Session = Depends(get_db)):
    """Gets the security and bottleneck anomalies list."""
    query = db.query(Anomaly)
    if store_id:
        query = query.filter(Anomaly.store_id == normalize_store_id(store_id))
    if resolved is not None:
        query = query.filter(Anomaly.resolved == resolved)
    return query.order_by(Anomaly.timestamp.desc()).all()

@app.post("/api/analytics/anomalies/{anomaly_id}/resolve")
def resolve_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    """Marks an active anomaly/alert as resolved."""
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anomaly.resolved = True
    db.commit()
    return {"status": "success", "message": f"Anomaly {anomaly_id} marked as resolved."}

@app.get("/api/analytics/realtime-charts")
def charts_api(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Generates historical time-series data of store occupancy and queue wait times."""
    store_norm = normalize_store_id(store_id) if store_id else "ST1076"
    
    # We aggregate footfall and occupancy by hour of the day
    events = db.query(Event).filter(
        Event.event_type.in_(["entry", "exit"]),
        Event.store_id == store_norm
    ).order_by(Event.timestamp).all()
    
    # Standard 24h timeline
    timeline = {i: {"hour": f"{i:02d}:00", "entries": 0, "exits": 0, "occupancy": 0} for i in range(8, 22)} # Store open 8am - 10pm
    
    curr_occupancy = 0
    for ev in events:
        hour = ev.timestamp.hour
        if hour in timeline:
            if ev.event_type == "entry":
                timeline[hour]["entries"] += 1
                curr_occupancy += 1
            else:
                timeline[hour]["exits"] += 1
                curr_occupancy = max(0, curr_occupancy - 1)
            timeline[hour]["occupancy"] = curr_occupancy
            
    # Flatten timeline dictionary to sorted list
    chart_data = [data for hour, data in sorted(timeline.items())]
    return chart_data

@app.post("/api/pipeline/reset-db")
def reset_db(db: Session = Depends(get_db)):
    """Clears all raw events and anomalies, retaining POS data."""
    db.query(Event).delete()
    db.query(Anomaly).delete()
    db.query(PosTransaction).delete()
    db.commit()
    
    # Re-seed POS
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for file in os.listdir(root_dir):
        if "transactions" in file and file.endswith(".csv"):
            load_pos_transactions(db, os.path.join(root_dir, file))
            break
            
    return {"status": "success", "message": "Database resetted. Raw events cleared."}

@app.post("/api/pipeline/simulate")
def start_simulation(background_tasks: BackgroundTasks):
    """Triggers the retail CCTV stream events simulation."""
    background_tasks.add_task(run_simulation)
    return {"status": "success", "message": "Simulation started in background."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
