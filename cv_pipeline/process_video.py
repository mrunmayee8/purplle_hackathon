import cv2
import os
import time
import requests
import json
import hashlib
from datetime import datetime, timedelta
from .detector import YOLODetector
from .tracker import CentroidTracker

# Setup API URL
API_URL = "http://localhost:8000/api/events"

# Standard Store Codes
STORES = {
    "Store 1": "store_1076",
    "Store 2": "store_1008"
}

def generate_demographics(track_id: int):
    """Deterministically generates demographic profiles based on track ID for consistency."""
    # Create MD5 hash of track ID to get stable pseudo-randomness
    h = hashlib.md5(str(track_id).encode()).hexdigest()
    val = int(h, 16)
    
    # 65% Female, 35% Male (matches retail makeup)
    gender = "F" if (val % 100) < 65 else "M"
    
    # Age range 16 - 65
    age = 18 + (val % 40)
    
    if age < 25:
        age_bucket = "18-24"
    elif age < 35:
        age_bucket = "25-34"
    elif age < 45:
        age_bucket = "35-44"
    elif age < 55:
        age_bucket = "45-54"
    else:
        age_bucket = "55+"
        
    is_staff = (val % 25) == 0  # 4% chance of being staff
    return gender, age, age_bucket, is_staff

def send_event(payload, log_file=None):
    """Sends event to the FastAPI server, logging locally if the server is offline."""
    # Write to local JSONL backup
    if log_file:
        with open(log_file, "a") as f:
            f.write(json.dumps(payload) + "\n")
            
    try:
        r = requests.post(API_URL, json=payload, timeout=2.0)
        if r.status_code == 201:
            print(f"Sent {payload['event_type']} event successfully for track {payload.get('track_id') or payload.get('id_token')}")
        else:
            print(f"API returned status {r.status_code} for event: {r.text}")
    except requests.exceptions.ConnectionError:
        print(f"Connection error. Saved {payload['event_type']} offline: ID {payload.get('track_id') or payload.get('id_token')}")

def process_cctv_feed(store_name: str, camera_name: str, video_path: str, max_frames=500):
    """Processes a single CCTV video feed and generates events."""
    store_code = STORES.get(store_name, "store_1008")
    
    # Backup logs file
    log_file = f"events_{store_code}_{camera_name}.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    print(f"--- Processing {store_name} | {camera_name} | Feed: {video_path} ---")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        return
        
    # Get metadata
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 5.0
    
    print(f"Resolution: {W}x{H} | Total Frames: {total_frames} | FPS: {fps}")
    
    # Load Detector and Tracker
    detector = YOLODetector(conf_threshold=0.35)
    tracker = CentroidTracker(max_disappeared=10, max_distance=150)
    
    # Track states for event emission
    triggered_entries = set()
    triggered_exits = set()
    inside_zones = {}  # track_id -> set of active zones
    zone_enters = {}   # (track_id, zone_id) -> start_timestamp
    
    # Billing queue states
    queue_joins = {}   # track_id -> join_time
    queue_served = {}  # track_id -> served_time
    queue_positions = {} # track_id -> position
    
    # Base datetime simulating a retail afternoon
    start_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    
    frame_idx = 0
    # Optimize: Process 1 frame per second (skip frames to run 5x faster on CPU)
    skip_rate = int(fps)
    
    while cap.isOpened() and frame_idx < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % skip_rate == 0:
            simulated_ts = start_time + timedelta(seconds=int(frame_idx / fps))
            sim_ts_str = simulated_ts.isoformat()
            
            # Detect
            boxes, confs = detector.detect_persons(frame)
            
            # Track
            tracks = tracker.update(boxes)
            
            # Identify current active tracks in queue area for position calculation
            active_queue_tracks = []
            
            # Process tracks
            for tid, track in list(tracks.items()):
                cx, cy = track.centroid
                gender, age, age_bucket, is_staff = generate_demographics(tid)
                
                # --- ENTRY / EXIT (CAM 3 in Store 1, entry in Store 2) ---
                if "entry" in camera_name.lower():
                    # Classify based on location in frame
                    # Say y < 500 is outside, y > 580 is inside. Crossing triggers events.
                    if cy > 580 and tid not in triggered_entries:
                        triggered_entries.add(tid)
                        payload = {
                            "event_type": "entry",
                            "id_token": f"ID_{tid}",
                            "store_code": store_code,
                            "camera_id": camera_name,
                            "event_timestamp": sim_ts_str,
                            "is_staff": is_staff,
                            "gender_pred": gender,
                            "age_pred": age,
                            "age_bucket": age_bucket,
                            "is_face_hidden": False,
                            "group_id": f"G_{tid//10}" if (tid % 7 == 0) else None,
                            "group_size": 2 if (tid % 7 == 0) else None
                        }
                        send_event(payload, log_file)
                        
                    elif cy < 500 and tid in triggered_entries and tid not in triggered_exits:
                        triggered_exits.add(tid)
                        payload = {
                            "event_type": "exit",
                            "id_token": f"ID_{tid}",
                            "store_code": store_code,
                            "camera_id": camera_name,
                            "event_timestamp": sim_ts_str,
                            "is_staff": is_staff,
                            "gender_pred": gender,
                            "age_pred": age,
                            "age_bucket": age_bucket,
                            "is_face_hidden": False,
                            "group_id": f"G_{tid//10}" if (tid % 7 == 0) else None,
                            "group_size": 2 if (tid % 7 == 0) else None
                        }
                        send_event(payload, log_file)
                
                # --- SHELF ZONES (CAM 1 & CAM 2 in Store 1, zone in Store 2) ---
                elif "zone" in camera_name.lower():
                    # Define shelves bounding boxes
                    # Store 1 CAM 1: left side is Left Shelf, right side is Lipstick Aisle
                    zones = []
                    if "cam 1" in camera_name.lower():
                        zones = [
                            {"id": "Z01", "name": "Left Shelf", "type": "SHELF", "rev": "Yes", "box": [50, 100, 800, 900]},
                            {"id": "Z03", "name": "Lipstick Aisle", "type": "SHELF", "rev": "Yes", "box": [1000, 100, 850, 900]}
                        ]
                    elif "cam 2" in camera_name.lower():
                        # Store 1 CAM 2: Center Display, Fragrance
                        zones = [
                            {"id": "Z02", "name": "Center Display", "type": "DISPLAY", "rev": "Yes", "box": [350, 200, 1100, 700]},
                            {"id": "Z04", "name": "Fragrance Section", "type": "SHELF", "rev": "Yes", "box": [50, 100, 280, 900]}
                        ]
                    else: # Store 2 zone.mp4
                        zones = [
                            {"id": "SZ01", "name": "Main Cosmetics Display", "type": "DISPLAY", "rev": "Yes", "box": [100, 200, 800, 800]}
                        ]
                        
                    for zone in zones:
                        zx, zy, zw, zh = zone["box"]
                        # Check if centroid is inside the zone box
                        in_zone = (zx <= cx <= zx + zw) and (zy <= cy <= zy + zh)
                        
                        active_zones = inside_zones.setdefault(tid, set())
                        z_id = zone["id"]
                        
                        if in_zone and z_id not in active_zones:
                            active_zones.add(z_id)
                            zone_enters[(tid, z_id)] = simulated_ts
                            
                            payload = {
                                "event_type": "zone_entered",
                                "track_id": tid,
                                "store_id": store_code,
                                "camera_id": camera_name,
                                "zone_id": f"{store_code.upper()}_{z_id}",
                                "zone_name": zone["name"],
                                "zone_type": zone["type"],
                                "is_revenue_zone": zone["rev"],
                                "event_time": sim_ts_str,
                                "zone_hotspot_x": float(cx),
                                "zone_hotspot_y": float(cy),
                                "gender": gender,
                                "age": age,
                                "age_bucket": age_bucket
                            }
                            send_event(payload, log_file)
                            
                        elif not in_zone and z_id in active_zones:
                            active_zones.remove(z_id)
                            enter_time = zone_enters.get((tid, z_id), simulated_ts)
                            duration = (simulated_ts - enter_time).total_seconds()
                            
                            payload = {
                                "event_type": "zone_exited",
                                "track_id": tid,
                                "store_id": store_code,
                                "camera_id": camera_name,
                                "zone_id": f"{store_code.upper()}_{z_id}",
                                "zone_name": zone["name"],
                                "zone_type": zone["type"],
                                "is_revenue_zone": zone["rev"],
                                "event_time": sim_ts_str,
                                "zone_hotspot_x": float(cx),
                                "zone_hotspot_y": float(cy),
                                "gender": gender,
                                "age": age,
                                "age_bucket": age_bucket
                            }
                            send_event(payload, log_file)
                            
                # --- CHECKOUT QUEUE (CAM 5 in Store 1, billing in Store 2) ---
                elif "billing" in camera_name.lower() or "checkout" in camera_name.lower():
                    # Billing Queue Box: x between 200 and 1200, y between 300 and 900
                    # Cash Register Point (Served): x between 800 and 1200, y between 300 and 600
                    in_queue = (200 <= cx <= 1200) and (300 <= cy <= 900)
                    in_service_area = (800 <= cx <= 1200) and (300 <= cy <= 600)
                    
                    if in_queue:
                        active_queue_tracks.append((tid, cy))  # Track ID and position in queue (depth)
                        
                        if tid not in queue_joins:
                            queue_joins[tid] = simulated_ts
                            queue_positions[tid] = len(active_queue_tracks)
                            
                        if in_service_area and tid not in queue_served:
                            queue_served[tid] = simulated_ts
                            
            # Calculate queue positions dynamically based on sorted y coordinate (closer to counter)
            # Counter is at the top (smaller y values)
            active_queue_tracks.sort(key=lambda item: item[1]) # Sort from lowest y to highest y
            for idx, (tid, _) in enumerate(active_queue_tracks):
                queue_positions[tid] = idx + 1
                
            # Handle tracks that disappeared from tracker (completed/abandoned checkout)
            active_tids = set(tracks.keys())
            for tid in list(queue_joins.keys()):
                if tid not in active_tids:
                    # They left the queue
                    join_time = queue_joins[tid]
                    exit_time = simulated_ts
                    wait_sec = int((exit_time - join_time).total_seconds())
                    
                    gender, age, age_bucket, is_staff = generate_demographics(tid)
                    
                    # If they reached the service area, they were served (completed checkout)
                    # Else they abandoned the queue
                    was_served = tid in queue_served
                    ev_type = "queue_completed" if was_served else "queue_abandoned"
                    
                    payload = {
                        "queue_event_id": f"QE_{tid}_{int(join_time.timestamp())}",
                        "event_type": ev_type,
                        "track_id": tid,
                        "store_id": store_code,
                        "camera_id": camera_name,
                        "zone_id": f"{store_code.upper()}_Z_BILLING_01",
                        "zone_name": "Billing Counter Queue",
                        "zone_type": "BILLING",
                        "is_revenue_zone": "Yes",
                        "queue_join_ts": join_time.isoformat(),
                        "queue_served_ts": queue_served[tid].isoformat() if was_served else None,
                        "queue_exit_ts": exit_time.isoformat(),
                        "wait_seconds": wait_sec,
                        "queue_position_at_join": queue_positions.get(tid, 1),
                        "abandoned": not was_served,
                        "zone_hotspot_x": 1000.0 if was_served else 500.0, # Approximate coordinates
                        "zone_hotspot_y": 450.0 if was_served else 600.0,
                        "gender": gender,
                        "age": age,
                        "age_bucket": age_bucket
                    }
                    send_event(payload, log_file)
                    
                    # Clean states
                    del queue_joins[tid]
                    if tid in queue_served:
                        del queue_served[tid]
                    if tid in queue_positions:
                        del queue_positions[tid]
                        
        frame_idx += 1
        
    cap.release()
    print(f"--- Completed processing {camera_name}. Feeds saved in {log_file} ---")

if __name__ == "__main__":
    # Test run on CAM 3 entry
    process_cctv_feed("Store 1", "CAM3_entry", "Store 1/CAM 3 - entry.mp4", max_frames=500)
