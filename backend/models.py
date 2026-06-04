from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)  # entry, exit, zone_entered, zone_exited, queue_completed, queue_abandoned
    store_id = Column(String, index=True)
    camera_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    
    # Tracking identifiers
    track_id = Column(Integer, index=True, nullable=True)
    id_token = Column(String, index=True, nullable=True)
    
    # Demographics and profile (from entry/exit/zone events)
    gender = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    age_bucket = Column(String, nullable=True)
    is_staff = Column(Boolean, default=False)
    is_face_hidden = Column(Boolean, default=False)
    
    # Group context
    group_id = Column(String, nullable=True)
    group_size = Column(Integer, nullable=True)
    
    # Zone context (for shelf/aisle and queue events)
    zone_id = Column(String, nullable=True)
    zone_name = Column(String, nullable=True)
    zone_type = Column(String, nullable=True)  # SHELF, DISPLAY, BILLING, etc.
    is_revenue_zone = Column(String, nullable=True) # "Yes" or "No"
    zone_hotspot_x = Column(Float, nullable=True)
    zone_hotspot_y = Column(Float, nullable=True)
    
    # Queue context
    queue_event_id = Column(String, nullable=True)
    queue_join_ts = Column(DateTime, nullable=True)
    queue_served_ts = Column(DateTime, nullable=True)
    queue_exit_ts = Column(DateTime, nullable=True)
    wait_seconds = Column(Float, nullable=True)
    queue_position_at_join = Column(Integer, nullable=True)
    abandoned = Column(Boolean, nullable=True)

class PosTransaction(Base):
    __tablename__ = "pos_transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    order_date = Column(String, index=True)  # format: DD-MM-YYYY
    order_time = Column(String, index=True)  # format: HH:MM:SS
    store_id = Column(String, index=True)
    product_id = Column(String)
    brand_name = Column(String)
    total_amount = Column(Float)

class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    anomaly_type = Column(String, index=True)  # loss_prevention, queue_bottleneck, long_dwell, staff_zone_breach
    severity = Column(String)  # LOW, MEDIUM, HIGH
    description = Column(String)
    track_id = Column(Integer, nullable=True)
    resolved = Column(Boolean, default=False)
