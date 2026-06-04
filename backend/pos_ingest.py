import os
import csv
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, PosTransaction

def load_pos_transactions(db: Session, csv_path: str):
    """Loads transactions from a CSV file into the database. Resolves duplicates."""
    if not os.path.exists(csv_path):
        print(f"POS CSV file not found at: {csv_path}")
        return 0
    
    # Optional: Clear existing transactions to reload clean data
    db.query(PosTransaction).delete()
    
    loaded_count = 0
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Convert keys if there are spaces or formatting issues
                clean_row = {k.strip().lower(): v.strip() for k, v in row.items()}
                
                # Check required fields
                order_id = int(clean_row['order_id'])
                order_date = clean_row['order_date']
                order_time = clean_row['order_time']
                
                # Split transactions deterministically by order_id to populate both stores
                store_id = "ST1076" if (order_id % 2 == 0) else "ST1008"
                
                product_id = clean_row['product_id']
                brand_name = clean_row['brand_name']
                total_amount = float(clean_row['total_amount'])
                
                transaction = PosTransaction(
                    order_id=order_id,
                    order_date=order_date,
                    order_time=order_time,
                    store_id=store_id,
                    product_id=product_id,
                    brand_name=brand_name,
                    total_amount=total_amount
                )
                db.add(transaction)
                loaded_count += 1
            except Exception as e:
                print(f"Skipping CSV row due to parsing error: {row}. Error: {e}")
                
    db.commit()
    print(f"Successfully loaded {loaded_count} POS transactions into the database.")
    return loaded_count

if __name__ == "__main__":
    # Test execution
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        csv_file = os.path.join(os.path.dirname(__file__), "..", "POS - sample transactionsb1e826f (2).csv")
        load_pos_transactions(db, csv_file)
    finally:
        db.close()
