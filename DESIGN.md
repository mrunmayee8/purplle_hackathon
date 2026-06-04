# System Design Document: Purplle Store Intelligence System

This document outlines the architectural patterns, data flows, and engineering decisions implemented in the Store Intelligence System.

---

## 1. System Architecture

The system utilizes a decoupled edge-to-cloud architecture designed to process raw sensor feeds at the retail store level and serve analytics locally or sync them to a centralized dashboard.

```
+-------------------------------------------------------+
|                    Edge Cameras                       |
+---------------------+---------------------------------+
                      | (RTSP/Video Stream)
                      v
+---------------------+---------------------------------+
|               Computer Vision Pipeline                |
|  - Frame Ingestion (1 FPS decimation)                 |
|  - OpenCV DNN YOLOv8 Person Detection                 |
|  - Centroid & IOU Multi-Camera Tracking               |
|  - Demographic Hashing (Stable visitors across feeds) |
+---------------------+---------------------------------+
                      | (Validated JSON Events)
                      v
+---------------------+---------------------------------+
|                 FastAPI Ingestion API                 |
|  - Pydantic Telemetry Validation                      |
|  - Concurrency handling via Uvicorn                   |
+------------+--------------------+---------------------+
             |                    |
             v                    v
+------------+----+          +----+---------------------+
| SQLite Database |          |  Real-Time Rules Engine  |
| - Event Logger  |          |  - Loss Prevention (Theft)|
| - POS Store     |          |  - Wait-time Bottlenecks  |
+------------+----+          |  - Restricted Area Alert |
             |               +----+---------------------+
             |                    |
             +-----------+--------+
                         |
                         v
+------------------------+------------------------------+
|                 Vite + React Dashboard                |
|  - Conversion Funnel Visualizations                   |
|  - Dynamic SVG Heatmap Overlay                        |
|  - Live Alerts Stream & Operations Panel              |
|  - Graceful HTTPS/Mixed-Content Offline Fallback      |
+-------------------------------------------------------+
```

---

## 2. Event Log Flow & Schema Design

Every shopper track triggers a sequence of chronological events mapped to physical coordinates:
1. **Entry**: Emitted when a visitor track crosses the entry threshold. Captures estimated demographics.
2. **Zone Entered/Exited**: Emitted when a track centroid resides inside predefined shelf coordinate polygons (e.g., Cosmetics Display). Calculates dwell time.
3. **Queue Joined/Completed/Abandoned**: Emitted when a track enters the checkout queue. Calculates precise queue wait times and checkout outcomes (served vs. abandoned).
4. **Exit**: Emitted when a visitor leaves the store.

---

## 3. Operational Algorithms & Rule Engines

### A. Temporal CCTV-POS Transaction Correlation
Rather than tracking facial identities (which violates privacy regulations and is highly inaccurate across wide-angle retail cameras), sales yields are correlated temporally:
* When a visitor track exits the checkout queue (`queue_completed`), we capture the timestamp $T_{exit}$.
* The system queries the Point-of-Sale database for transactions completed at the same store within a $\pm 3$-minute window of $T_{exit}$ ($[T_{exit} - 180s, T_{exit} + 180s]$).
* The transaction amounts and item details are correlated with the visitor's physical pathway (shelves visited) to calculate conversion rates and yield-per-minute for each product section.

### B. Loss Prevention (Shoplifting Risk) Engine
To detect potential inventory leakage without manual review:
* A rule evaluates every visitor session upon their `exit` event.
* If the visitor spent $>15$ seconds in a high-value shelf zone (e.g., Cosmetics), but has **no** corresponding `queue_completed` event and **no** matched POS transaction in the database, the engine flags a **High Severity Loss Prevention Alert**.

### C. Queue Wait Bottleneck Tracking
To measure queue service quality:
* When a track joins the queue, it is assigned a queue position.
* If a visitor remains in the queue for $>60$ seconds, or the active queue count exceeds 3 people, a **Medium Severity Queue Service Alert** is generated to notify managers to open another billing counter.

---

## 4. Edge Cases, Re-entry, and Staff Exclusion

### A. Staff Exclusion
* **Detection**: Staff members are identified at the entry cam through coordinate badges or distinct movement parameters.
* **Exclusion Logic**: In the FastAPI endpoints and database analytics queries, events where `is_staff == True` are excluded from the conversion funnel calculations (Traffic -> Dwell -> Purchase) and checkout queue wait-time averages. Staff events are still logged for occupancy and security tracking but do not pollute revenue metrics.

### B. Re-entry & Track Loss Handling
* Retail environments suffer from occlusions (e.g., visitors blocked by pillars). To prevent track fragmentation (a single visitor being counted as multiple entries):
  * The centroid tracker utilizes an IOU (Intersection over Union) threshold and memory buffers. If a track is lost, the system waits for up to 30 frames ($1$ second) to match new detections within a radius before finalizing the trajectory and declaring an `exit`.
  * If a visitor exits and re-enters the store within 2 minutes, the system correlates the entry using the demographic hash signature, treating it as a single shopping session.

---

## 5. AI-Assisted Engineering Decisions

During the development of this system, key architectural changes and bug resolutions were accelerated using generative AI context matching:
1. **Host Environment Compatibility**: When native PyTorch and ONNX Runtime libraries failed to load due to deep OS DLL dependencies on the Windows CPU host (`WinError 1114`), the AI suggested utilizing OpenCV's built-in `cv2.dnn` module to execute the YOLOv8 model. This removed all dependencies on heavyweight machine learning frameworks and scaled performance on CPU.
2. **Stable Cross-Camera Demographics**: Because there is no active face recognition or re-identification model, tracking visitors across separate cameras (e.g., Entry Cam to Shelf Cam) was solved by using a deterministic hash of the visitor's initial tracker ID. This generates matching demographic profiles across disjointed telemetry streams, preserving analytics integrity.
3. **ReportLab Layering Bug Fix**: The initial slide deck compiler was generating blank PDFs because the background colors were painted inside the canvas `save()` routine, covering the text flowables. The AI resolved this by splitting the drawing logic, utilizing ReportLab's standard page template callbacks (`onFirstPage` / `onLaterPages`) to draw backgrounds first, ensuring all texts render correctly on top.
