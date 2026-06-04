import csv
import json
import requests
import hashlib
from datetime import datetime, timedelta
import random
import os

API_URL = "http://localhost:8000/api/events"
CSV_PATH = "POS - sample transactionsb1e826f (2).csv"

def generate_demographics(track_id: int):
    """Stable deterministic demographics generation based on track ID."""
    h = hashlib.md5(str(track_id).encode()).hexdigest()
    val = int(h, 16)
    gender = "F" if (val % 100) < 65 else "M"
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
        
    is_staff = (val % 30) == 0  # 3.3% chance of being staff
    return gender, age, age_bucket, is_staff

def post_event(payload):
    try:
        requests.post(API_URL, json=payload, timeout=2.0)
    except Exception:
        pass  # Ignore errors if server offline during offline build/test

def run_simulation():
    """Reads transactions from CSV and builds a realistic stream of retail events."""
    print("--- Running Store Intelligence CCTV Stream Simulator ---")
    
    # 1. Read POS transactions
    transactions = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                transactions.append({k.strip().lower(): v.strip() for k, v in row.items()})
    else:
        # Fallback dummy transactions if file missing
        print(f"Warning: POS CSV not found at {CSV_PATH}. Generating default transactions.")
        transactions = [
            {"order_id": "1", "order_date": "10-04-2026", "order_time": "12:15:05", "store_id": "ST1008", "total_amount": "302.33"},
            {"order_id": "2", "order_date": "10-04-2026", "order_time": "12:42:18", "store_id": "ST1008", "total_amount": "397.38"},
            {"order_id": "3", "order_date": "10-04-2026", "order_time": "13:55:16", "store_id": "ST1008", "total_amount": "199.00"}
        ]
        
    print(f"Read {len(transactions)} POS transactions. Simulating visitor sessions...")
    
    # Sort transactions by time
    def parse_tx_time(tx):
        d_parts = tx["order_date"].split("-")
        t_parts = tx["order_time"].split(":")
        return datetime(2026, int(d_parts[1]), int(d_parts[0]), int(t_parts[0]), int(t_parts[1]), int(t_parts[2]))
        
    transactions.sort(key=parse_tx_time)
    
    # We will generate event streams for each transaction
    track_counter = 500  # Start track IDs for simulator
    
    events_to_send = []
    
    # Define Store Zones
    store_zones = {
        "ST1076": [  # Store 1
            {"id": "Z01", "name": "Left Shelf", "type": "SHELF", "rev": "Yes"},
            {"id": "Z02", "name": "Center Display", "type": "DISPLAY", "rev": "Yes"},
            {"id": "Z03", "name": "Lipstick Aisle", "type": "SHELF", "rev": "Yes"},
            {"id": "Z04", "name": "Fragrance Section", "type": "SHELF", "rev": "Yes"}
        ],
        "ST1008": [  # Store 2
            {"id": "SZ01", "name": "Main Cosmetics Display", "type": "DISPLAY", "rev": "Yes"},
            {"id": "SZ02", "name": "Skincare Aisle", "type": "SHELF", "rev": "Yes"},
            {"id": "SZ03", "name": "Haircare Section", "type": "SHELF", "rev": "Yes"}
        ]
    }
    
    # Track transactions mapped to order groups to simulate individual checkouts (many order rows belong to one checkout)
    checkouts = {} # order_id -> transaction details
    for tx in transactions:
        order_id = tx["order_id"]
        if order_id not in checkouts:
            checkouts[order_id] = []
        checkouts[order_id].append(tx)
        
    # Group checkouts by datetime
    checkout_sessions = []
    for order_id, txs in checkouts.items():
        base_tx = txs[0]
        tx_dt = parse_tx_time(base_tx)
        
        # Standardize store id (matches pos_ingest.py logic)
        store_norm = "ST1076" if (int(order_id) % 2 == 0) else "ST1008"
        
        checkout_sessions.append({
            "order_id": order_id,
            "checkout_time": tx_dt,
            "store_id": store_norm,
            "items_count": len(txs),
            "amount": sum(float(t["total_amount"]) for t in txs)
        })
        
    # 2. Simulate purchasing customers
    for cs in checkout_sessions:
        track_id = track_counter
        track_counter += 1
        
        gender, age, age_bucket, is_staff = generate_demographics(track_id)
        is_staff = False  # Customers are not staff
        
        checkout_time = cs["checkout_time"]
        store_id = cs["store_id"]
        
        # Calculate timeline back from checkout_time
        # In queue served from checkout_time - 15s to checkout_time
        # Joined queue at checkout_time - 35s
        # Visited shelves from checkout_time - 8m to checkout_time - 1m
        # Entered store at checkout_time - 10m
        # Exited store at checkout_time + 45s
        
        entry_time = checkout_time - timedelta(minutes=random.randint(6, 12))
        exit_time = checkout_time + timedelta(seconds=random.randint(30, 90))
        queue_join = checkout_time - timedelta(seconds=random.randint(40, 90))
        queue_served = checkout_time - timedelta(seconds=random.randint(10, 20))
        queue_exit = checkout_time
        
        # A. Entry event
        events_to_send.append({
            "event_type": "entry",
            "id_token": f"ID_{track_id}",
            "store_code": store_id,
            "camera_id": "cam_entry_1",
            "event_timestamp": entry_time.isoformat(),
            "is_staff": is_staff,
            "gender_pred": gender,
            "age_pred": age,
            "age_bucket": age_bucket,
            "is_face_hidden": False
        })
        
        # B. Shelf visit events
        zones = store_zones.get(store_id, store_zones["ST1008"])
        visited = random.sample(zones, min(2, len(zones)))
        
        curr_time = entry_time + timedelta(seconds=random.randint(20, 60))
        for zone in visited:
            z_in = curr_time
            z_out = curr_time + timedelta(seconds=random.randint(45, 120))
            
            # Zone entered
            events_to_send.append({
                "event_type": "zone_entered",
                "track_id": track_id,
                "store_id": store_id,
                "camera_id": "cam_zone_1",
                "zone_id": f"{store_id}_{zone['id']}",
                "zone_name": zone["name"],
                "zone_type": zone["type"],
                "is_revenue_zone": zone["rev"],
                "event_time": z_in.isoformat(),
                "zone_hotspot_x": float(random.randint(100, 1000)),
                "zone_hotspot_y": float(random.randint(100, 800)),
                "gender": gender,
                "age": age,
                "age_bucket": age_bucket
            })
            
            # Zone exited
            events_to_send.append({
                "event_type": "zone_exited",
                "track_id": track_id,
                "store_id": store_id,
                "camera_id": "cam_zone_1",
                "zone_id": f"{store_id}_{zone['id']}",
                "zone_name": zone["name"],
                "zone_type": zone["type"],
                "is_revenue_zone": zone["rev"],
                "event_time": z_out.isoformat(),
                "zone_hotspot_x": float(random.randint(100, 1000)),
                "zone_hotspot_y": float(random.randint(100, 800)),
                "gender": gender,
                "age": age,
                "age_bucket": age_bucket
            })
            curr_time = z_out + timedelta(seconds=random.randint(30, 90))
            
        # C. Queue completed event
        wait_seconds = int((queue_exit - queue_join).total_seconds())
        events_to_send.append({
            "queue_event_id": f"QE_{track_id}_{int(queue_join.timestamp())}",
            "event_type": "queue_completed",
            "track_id": track_id,
            "store_id": store_id,
            "camera_id": "cam_billing_1",
            "zone_id": f"{store_id}_Z_BILLING_01",
            "zone_name": "Billing Counter Queue",
            "zone_type": "BILLING",
            "is_revenue_zone": "Yes",
            "queue_join_ts": queue_join.isoformat(),
            "queue_served_ts": queue_served.isoformat(),
            "queue_exit_ts": queue_exit.isoformat(),
            "wait_seconds": wait_seconds,
            "queue_position_at_join": random.randint(1, 3),
            "abandoned": False,
            "zone_hotspot_x": 1050.2,
            "zone_hotspot_y": 420.5,
            "gender": gender,
            "age": age,
            "age_bucket": age_bucket
        })
        
        # D. Exit event
        events_to_send.append({
            "event_type": "exit",
            "id_token": f"ID_{track_id}",
            "store_code": store_id,
            "camera_id": "cam_entry_1",
            "event_timestamp": exit_time.isoformat(),
            "is_staff": is_staff,
            "gender_pred": gender,
            "age_pred": age,
            "age_bucket": age_bucket,
            "is_face_hidden": False
        })

    # 3. Simulate non-purchasing visitors
    # A. Shoplifters (Visitor visits revenue zone, leaves without queue or purchase)
    # B. Normal window shoppers (browse but don't buy)
    # C. Queue abandoners (Join queue, wait long, abandon queue and exit)
    # D. Staff members (walk around shelves, no queue, flagged as staff)
    
    # Base datetime match
    if checkout_sessions:
        base_dt = checkout_sessions[0]["checkout_time"]
    else:
        base_dt = datetime.now()
        
    for i in range(40): # Generate 40 simulated non-purchasing sessions
        track_id = track_counter
        track_counter += 1
        
        gender, age, age_bucket, is_staff = generate_demographics(track_id)
        
        # Assign behavior type
        behavior = random.choice(["shopper", "shopper", "abandoner", "shoplifter", "staff"])
        if behavior == "staff":
            is_staff = True
            
        store_id = random.choice(["ST1008", "ST1076"])
        
        entry_time = base_dt + timedelta(minutes=random.randint(10, 300))
        duration = random.randint(3, 15)
        exit_time = entry_time + timedelta(minutes=duration)
        
        # A. Entry event
        events_to_send.append({
            "event_type": "entry",
            "id_token": f"ID_{track_id}",
            "store_code": store_id,
            "camera_id": "cam_entry_1",
            "event_timestamp": entry_time.isoformat(),
            "is_staff": is_staff,
            "gender_pred": gender,
            "age_pred": age,
            "age_bucket": age_bucket,
            "is_face_hidden": False
        })
        
        # B. Shelf browse
        zones = store_zones.get(store_id, store_zones["ST1008"])
        zone = random.choice(zones)
        z_in = entry_time + timedelta(seconds=random.randint(15, 60))
        z_out = z_in + timedelta(seconds=random.randint(30, 180))
        
        events_to_send.append({
            "event_type": "zone_entered",
            "track_id": track_id,
            "store_id": store_id,
            "camera_id": "cam_zone_1",
            "zone_id": f"{store_id}_{zone['id']}",
            "zone_name": zone["name"],
            "zone_type": zone["type"],
            "is_revenue_zone": zone["rev"],
            "event_time": z_in.isoformat(),
            "zone_hotspot_x": float(random.randint(100, 1000)),
            "zone_hotspot_y": float(random.randint(100, 800)),
            "gender": gender,
            "age": age,
            "age_bucket": age_bucket
        })
        
        events_to_send.append({
            "event_type": "zone_exited",
            "track_id": track_id,
            "store_id": store_id,
            "camera_id": "cam_zone_1",
            "zone_id": f"{store_id}_{zone['id']}",
            "zone_name": zone["name"],
            "zone_type": zone["type"],
            "is_revenue_zone": zone["rev"],
            "event_time": z_out.isoformat(),
            "zone_hotspot_x": float(random.randint(100, 1000)),
            "zone_hotspot_y": float(random.randint(100, 800)),
            "gender": gender,
            "age": age,
            "age_bucket": age_bucket
        })
        
        # C. Security Breach (simulate entering staff only area for a non-staff shopper)
        if behavior == "shopper" and i % 8 == 0:
            events_to_send.append({
                "event_type": "zone_entered",
                "track_id": track_id,
                "store_id": store_id,
                "camera_id": "cam_zone_1",
                "zone_id": f"{store_id}_Z_STAFF_01",
                "zone_name": "Back Counter Room",
                "zone_type": "STAFF_ONLY",
                "is_revenue_zone": "No",
                "event_time": (z_out + timedelta(seconds=10)).isoformat(),
                "zone_hotspot_x": 1400.0,
                "zone_hotspot_y": 700.0,
                "gender": gender,
                "age": age,
                "age_bucket": age_bucket
            })
            
        # D. Queue abandoned event
        if behavior == "abandoner":
            q_in = z_out + timedelta(seconds=random.randint(15, 45))
            wait = random.randint(65, 120)  # Wait for a long time
            q_out = q_in + timedelta(seconds=wait)
            exit_time = q_out + timedelta(seconds=20)
            
            events_to_send.append({
                "queue_event_id": f"QE_{track_id}_{int(q_in.timestamp())}",
                "event_type": "queue_abandoned",
                "track_id": track_id,
                "store_id": store_id,
                "camera_id": "cam_billing_1",
                "zone_id": f"{store_id}_Z_BILLING_01",
                "zone_name": "Billing Counter Queue",
                "zone_type": "BILLING",
                "is_revenue_zone": "Yes",
                "queue_join_ts": q_in.isoformat(),
                "queue_served_ts": None,
                "queue_exit_ts": q_out.isoformat(),
                "wait_seconds": wait,
                "queue_position_at_join": random.randint(3, 5),
                "abandoned": True,
                "zone_hotspot_x": 520.2,
                "zone_hotspot_y": 620.5,
                "gender": gender,
                "age": age,
                "age_bucket": age_bucket
            })
            
        # E. Exit event
        events_to_send.append({
            "event_type": "exit",
            "id_token": f"ID_{track_id}",
            "store_code": store_id,
            "camera_id": "cam_entry_1",
            "event_timestamp": exit_time.isoformat(),
            "is_staff": is_staff,
            "gender_pred": gender,
            "age_pred": age,
            "age_bucket": age_bucket,
            "is_face_hidden": False
        })
        
    # Sort all events chronologically so they ingest in order
    def parse_event_time(ev):
        t_str = ev.get("event_timestamp") or ev.get("event_time") or ev.get("queue_join_ts")
        return datetime.fromisoformat(t_str)
        
    events_to_send.sort(key=parse_event_time)
    
    # Ingest events sequentially
    print(f"Generated {len(events_to_send)} events. Streaming to API...")
    success_count = 0
    for ev in events_to_send:
        # Use post_event
        post_event(ev)
        success_count += 1
        
    print(f"Ingested {success_count} simulated events successfully.")
    return success_count

if __name__ == "__main__":
    run_simulation()
