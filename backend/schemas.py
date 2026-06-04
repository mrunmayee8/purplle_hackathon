from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventCreate(BaseModel):
    event_type: str  # entry, exit, zone_entered, zone_exited, queue_completed, queue_abandoned
    
    # Store and Camera Identifiers (support both store_code and store_id)
    store_code: Optional[str] = None
    store_id: Optional[str] = None
    camera_id: str
    
    # Timestamps (support both event_timestamp, event_time, queue_join_ts, etc.)
    event_timestamp: Optional[str] = None
    event_time: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    # Tracking identifiers
    track_id: Optional[int] = None
    id_token: Optional[str] = None
    
    # Demographics (support both gender/gender_pred and age/age_pred)
    gender: Optional[str] = None
    gender_pred: Optional[str] = None
    age: Optional[int] = None
    age_pred: Optional[int] = None
    age_bucket: Optional[str] = None
    is_staff: Optional[bool] = False
    is_face_hidden: Optional[bool] = False
    
    # Group Info
    group_id: Optional[str] = None
    group_size: Optional[int] = None
    
    # Zone context
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None  # SHELF, DISPLAY, BILLING, etc.
    is_revenue_zone: Optional[str] = None  # "Yes" or "No"
    zone_hotspot_x: Optional[float] = None
    zone_hotspot_y: Optional[float] = None
    
    # Queue context
    queue_event_id: Optional[str] = None
    queue_join_ts: Optional[str] = None
    queue_served_ts: Optional[str] = None
    queue_exit_ts: Optional[str] = None
    wait_seconds: Optional[float] = None
    queue_position_at_join: Optional[int] = None
    abandoned: Optional[bool] = None

class EventResponse(BaseModel):
    id: int
    event_type: str
    store_id: str
    camera_id: str
    timestamp: datetime
    track_id: Optional[int] = None
    id_token: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    age_bucket: Optional[str] = None
    is_staff: bool
    zone_name: Optional[str] = None
    wait_seconds: Optional[float] = None
    abandoned: Optional[bool] = None

    class Config:
        from_attributes = True

class PosTransactionCreate(BaseModel):
    order_id: int
    order_date: str
    order_time: str
    store_id: str
    product_id: str
    brand_name: str
    total_amount: float

class PosTransactionResponse(BaseModel):
    id: int
    order_id: int
    order_date: str
    order_time: str
    store_id: str
    product_id: str
    brand_name: str
    total_amount: float

    class Config:
        from_attributes = True

class AnomalyResponse(BaseModel):
    id: int
    store_id: str
    timestamp: datetime
    anomaly_type: str
    severity: str
    description: str
    track_id: Optional[int] = None
    resolved: bool

    class Config:
        from_attributes = True

class SummaryKPIs(BaseModel):
    total_footfall: int
    active_occupancy: int
    conversion_rate: float
    avg_dwell_time_seconds: float
    avg_queue_wait_seconds: float
    queue_abandonment_rate: float
    total_revenue: float
    transaction_count: int

class ZoneAnalytics(BaseModel):
    zone_id: str
    zone_name: str
    zone_type: str
    is_revenue_zone: str
    visitor_count: int
    avg_dwell_seconds: float
    conversion_rate: Optional[float] = None

class FunnelStage(BaseModel):
    stage_name: str
    visitor_count: int
    percentage_of_total: float
