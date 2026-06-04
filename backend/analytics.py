from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any
from .models import Event, PosTransaction, Anomaly

def parse_iso_datetime(dt_str) -> datetime:
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    try:
        # Try to parse standard ISO format with decimals
        return datetime.fromisoformat(dt_str.replace('Z', ''))
    except Exception:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            try:
                return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                return None

def normalize_store_id(store_id: str) -> str:
    """Normalizes store_id format (e.g. ST1076, store_1076, store_1008)"""
    if not store_id:
        return ""
    store_id = store_id.strip().lower()
    # Extract digits
    digits = "".join([c for c in store_id if c.isdigit()])
    return f"ST{digits}"

def get_visitor_sessions(db: Session, store_id: str = None) -> List[Dict[str, Any]]:
    """
    Groups entry/exit events into unified visitor sessions, and associates 
    shelf/queue tracks using spatial-temporal and demographic correlation.
    """
    # Normalize requested store_id
    norm_req_store = normalize_store_id(store_id) if store_id else None

    # Get entries
    entries_query = db.query(Event).filter(Event.event_type == "entry")
    if norm_req_store:
        # Match stores
        entries = [e for e in entries_query.all() if normalize_store_id(e.store_id or e.camera_id) == norm_req_store]
    else:
        entries = entries_query.all()
        
    sessions = []
    for entry in entries:
        # Find matching exit for this id_token
        exit_event = db.query(Event).filter(
            Event.event_type == "exit",
            Event.id_token == entry.id_token
        ).first()
        
        # If no exit, estimate it or assume active
        entry_time = entry.timestamp
        exit_time = exit_event.timestamp if exit_event else entry_time + timedelta(minutes=15)
        is_active = exit_event is None
        
        # Demographics
        gender = entry.gender or "F"
        age = entry.age or 25
        age_bucket = entry.age_bucket or "25-34"
        is_staff = entry.is_staff
        
        # Correlate tracks active in the store during this time frame
        # We query zone entered/exited and queue events
        norm_store = normalize_store_id(entry.store_id or entry.camera_id)
        
        # Find tracks matching demographics and store in this time window
        tracks_query = db.query(Event.track_id).filter(
            Event.event_type.in_(["zone_entered", "queue_completed", "queue_abandoned"]),
            Event.timestamp >= entry_time - timedelta(minutes=1),
            Event.timestamp <= exit_time + timedelta(minutes=2),
            Event.gender == gender
        ).distinct()
        
        matching_tracks = [t[0] for t in tracks_query.all() if t[0] is not None]
        
        # Gather all zone visits for these tracks
        zone_events = db.query(Event).filter(
            Event.track_id.in_(matching_tracks),
            Event.event_type.in_(["zone_entered", "zone_exited"])
        ).order_by(Event.timestamp).all()
        
        # Gather queue events
        queue_events = db.query(Event).filter(
            Event.track_id.in_(matching_tracks),
            Event.event_type.in_(["queue_completed", "queue_abandoned"])
        ).order_by(Event.timestamp).all()
        
        # Calculate zone metrics
        visited_zones = []
        dwell_times = {}
        
        # Process shelf dwells
        enters = {}
        for ze in zone_events:
            z_id = ze.zone_id
            if ze.event_type == "zone_entered":
                enters[z_id] = ze.timestamp
            elif ze.event_type == "zone_exited" and z_id in enters:
                duration = (ze.timestamp - enters[z_id]).total_seconds()
                dwell_times[z_id] = dwell_times.get(z_id, 0.0) + duration
                if z_id not in [vz["zone_id"] for vz in visited_zones]:
                    visited_zones.append({
                        "zone_id": z_id,
                        "zone_name": ze.zone_name,
                        "zone_type": ze.zone_type,
                        "is_revenue_zone": ze.is_revenue_zone
                    })
                del enters[z_id]
                
        # Parse queue metrics
        queue_joined = False
        queue_completed = False
        queue_wait = 0.0
        queue_abandoned = False
        queue_exit_time = None
        
        for qe in queue_events:
            queue_joined = True
            queue_wait = qe.wait_seconds or 0.0
            queue_exit_time = qe.queue_exit_ts or qe.timestamp
            if qe.event_type == "queue_completed":
                queue_completed = True
            elif qe.event_type == "queue_abandoned":
                queue_abandoned = True
                
        # Try to correlate with POS Transactions
        matched_transaction = None
        if queue_completed and queue_exit_time:
            # Look for transaction in POS at the same store (+/- 3 minutes of queue checkout)
            q_time = parse_iso_datetime(queue_exit_time) if isinstance(queue_exit_time, str) else queue_exit_time
            if q_time:
                # Find all transactions
                txs = db.query(PosTransaction).all()
                for tx in txs:
                    if normalize_store_id(tx.store_id) == norm_store:
                        # Parse transaction time
                        try:
                            # format order_date: DD-MM-YYYY, order_time: HH:MM:SS
                            # Let's assume order date matches event date
                            d_parts = tx.order_date.split('-')
                            t_parts = tx.order_time.split(':')
                            tx_time = datetime(q_time.year, int(d_parts[1]), int(d_parts[0]), int(t_parts[0]), int(t_parts[1]), int(t_parts[2]))
                            
                            time_diff = abs((tx_time - q_time).total_seconds())
                            if time_diff <= 180: # 3 minute window
                                matched_transaction = tx
                                break
                        except Exception:
                            continue
                            
        sessions.append({
            "id_token": entry.id_token,
            "store_id": norm_store,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "is_active": is_active,
            "gender": gender,
            "age": age,
            "age_bucket": age_bucket,
            "is_staff": is_staff,
            "visited_zones": visited_zones,
            "zone_dwells": dwell_times,
            "queue_joined": queue_joined,
            "queue_completed": queue_completed,
            "queue_abandoned": queue_abandoned,
            "queue_wait": queue_wait,
            "converted": matched_transaction is not None,
            "revenue": matched_transaction.total_amount if matched_transaction else 0.0,
            "transaction": matched_transaction
        })
        
    return sessions

def get_summary_analytics(db: Session, store_id: str = None) -> Dict[str, Any]:
    sessions = get_visitor_sessions(db, store_id)
    non_staff_sessions = [s for s in sessions if not s["is_staff"]]
    
    total_footfall = len(non_staff_sessions)
    active_occupancy = len([s for s in non_staff_sessions if s["is_active"]])
    
    conversions = [s for s in non_staff_sessions if s["converted"]]
    conversion_rate = (len(conversions) / total_footfall * 100) if total_footfall > 0 else 0.0
    
    dwell_times = [(s["exit_time"] - s["entry_time"]).total_seconds() for s in non_staff_sessions]
    avg_dwell = (sum(dwell_times) / len(dwell_times)) if dwell_times else 0.0
    
    queue_joins = [s for s in non_staff_sessions if s["queue_joined"]]
    completed_queues = [s for s in queue_joins if s["queue_completed"]]
    abandoned_queues = [s for s in queue_joins if s["queue_abandoned"]]
    
    avg_queue_wait = (sum([s["queue_wait"] for s in completed_queues]) / len(completed_queues)) if completed_queues else 0.0
    queue_abandon_rate = (len(abandoned_queues) / len(queue_joins) * 100) if queue_joins else 0.0
    
    total_revenue = sum([s["revenue"] for s in non_staff_sessions])
    transaction_count = len(conversions)
    
    return {
        "total_footfall": total_footfall,
        "active_occupancy": active_occupancy,
        "conversion_rate": round(conversion_rate, 2),
        "avg_dwell_time_seconds": round(avg_dwell, 1),
        "avg_queue_wait_seconds": round(avg_queue_wait, 1),
        "queue_abandonment_rate": round(queue_abandon_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "transaction_count": transaction_count
    }

def get_zone_analytics(db: Session, store_id: str = None) -> List[Dict[str, Any]]:
    sessions = get_visitor_sessions(db, store_id)
    non_staff_sessions = [s for s in sessions if not s["is_staff"]]
    
    # Aggregate by zone
    zones_data = {}
    for s in non_staff_sessions:
        for vz in s["visited_zones"]:
            z_id = vz["zone_id"]
            if z_id not in zones_data:
                zones_data[z_id] = {
                    "zone_id": z_id,
                    "zone_name": vz["zone_name"],
                    "zone_type": vz["zone_type"],
                    "is_revenue_zone": vz["is_revenue_zone"],
                    "visitor_count": 0,
                    "total_dwell": 0.0,
                    "conversions": 0
                }
            zones_data[z_id]["visitor_count"] += 1
            zones_data[z_id]["total_dwell"] += s["zone_dwells"].get(z_id, 0.0)
            if s["converted"]:
                zones_data[z_id]["conversions"] += 1
                
    result = []
    for z_id, data in zones_data.items():
        v_count = data["visitor_count"]
        result.append({
            "zone_id": z_id,
            "zone_name": data["zone_name"],
            "zone_type": data["zone_type"],
            "is_revenue_zone": data["is_revenue_zone"],
            "visitor_count": v_count,
            "avg_dwell_seconds": round(data["total_dwell"] / v_count, 1) if v_count > 0 else 0.0,
            "conversion_rate": round(data["conversions"] / v_count * 100, 2) if v_count > 0 else 0.0
        })
        
    # Sort by visitor count descending
    result.sort(key=lambda x: x["visitor_count"], reverse=True)
    return result

def get_funnel_analytics(db: Session, store_id: str = None) -> List[Dict[str, Any]]:
    sessions = get_visitor_sessions(db, store_id)
    non_staff = [s for s in sessions if not s["is_staff"]]
    total = len(non_staff)
    
    # 1. Traffic (Entries)
    traffic_count = total
    
    # 2. Engaged (Spent > 10s in any shelf zone)
    engaged_count = len([
        s for s in non_staff 
        if any(dwell > 10 for dwell in s["zone_dwells"].values())
    ])
    
    # 3. Queue (Joined billing queue)
    queue_count = len([s for s in non_staff if s["queue_joined"]])
    
    # 4. Conversion (Completed transaction)
    converted_count = len([s for s in non_staff if s["converted"]])
    
    funnel = [
        {"stage_name": "Store Visits (Traffic)", "visitor_count": traffic_count, "percentage_of_total": 100.0},
        {"stage_name": "Product Engagement", "visitor_count": engaged_count, "percentage_of_total": round(engaged_count / traffic_count * 100, 1) if traffic_count > 0 else 0.0},
        {"stage_name": "Checkout Queue", "visitor_count": queue_count, "percentage_of_total": round(queue_count / traffic_count * 100, 1) if traffic_count > 0 else 0.0},
        {"stage_name": "Purchases (Converted)", "visitor_count": converted_count, "percentage_of_total": round(converted_count / traffic_count * 100, 1) if traffic_count > 0 else 0.0}
    ]
    return funnel

def run_anomaly_detection(db: Session, store_id: str = None):
    """
    Evaluates current session data and active queue logs to detect 
    security breaches, service bottlenecks, and loss prevention alerts.
    """
    sessions = get_visitor_sessions(db, store_id)
    
    # 1. Shoplifting / Loss Prevention Alert
    # Non-staff customer who engaged with revenue shelf zones but did NOT join queue and exited without converting
    for s in sessions:
        if s["is_staff"] or s["is_active"]:
            continue
        
        # Check if they engaged with shelves
        visited_revenue_zones = [z for z in s["visited_zones"] if z["is_revenue_zone"] == "Yes"]
        
        if visited_revenue_zones and not s["queue_joined"] and not s["converted"]:
            # Check if this anomaly already logged
            exists = db.query(Anomaly).filter(
                Anomaly.anomaly_type == "loss_prevention",
                Anomaly.track_id == s["id_token"]
            ).first()
            if not exists:
                zones_str = ", ".join([z["zone_name"] for z in visited_revenue_zones])
                desc = f"Visitor '{s['id_token']}' visited revenue zone(s) [{zones_str}] for average {round(sum(s['zone_dwells'].values()), 1)}s, but exited store without queueing or purchasing."
                
                anomaly = Anomaly(
                    store_id=s["store_id"],
                    anomaly_type="loss_prevention",
                    severity="HIGH",
                    description=desc,
                    track_id=None # We can store id_token as a hash or reference
                )
                db.add(anomaly)
                
    # 2. Queue bottlenecks
    # Wait times over 60 seconds
    high_wait_sessions = [s for s in sessions if s["queue_completed"] and s["queue_wait"] > 60]
    for s in high_wait_sessions:
        exists = db.query(Anomaly).filter(
            Anomaly.anomaly_type == "queue_bottleneck",
            Anomaly.description.contains(s["id_token"])
        ).first()
        if not exists:
            desc = f"Customer '{s['id_token']}' experienced checkout bottleneck waiting {round(s['queue_wait'])}s in checkout queue."
            anomaly = Anomaly(
                store_id=s["store_id"],
                anomaly_type="queue_bottleneck",
                severity="MEDIUM",
                description=desc
            )
            db.add(anomaly)
            
    # 3. Staff zone breaches
    # If standard customer enters a zone defined as staff-only (e.g. Back Counter)
    # We will simulate this by checking if the coordinate values fall in forbidden zone (processed in CV)
    # If the Event has a zone_id = 'staff_only' and is_staff is False, trigger it.
    breach_events = db.query(Event).filter(
        Event.event_type == "zone_entered",
        Event.zone_id.contains("staff"),
        Event.is_staff == False
    ).all()
    
    for be in breach_events:
        exists = db.query(Anomaly).filter(
            Anomaly.anomaly_type == "staff_zone_breach",
            Anomaly.track_id == be.track_id
        ).first()
        if not exists:
            desc = f"Security Breach: Non-staff Track {be.track_id} entered designated staff-only zone: {be.zone_name}."
            anomaly = Anomaly(
                store_id=normalize_store_id(be.store_id or be.camera_id),
                anomaly_type="staff_zone_breach",
                severity="HIGH",
                description=desc,
                track_id=be.track_id
            )
            db.add(anomaly)
            
    db.commit()
