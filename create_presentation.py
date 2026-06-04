import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Draw background color (except on cover page 1)
        self.saveState()
        self.setFillColor(colors.HexColor("#08070d"))
        self.rect(0, 0, 792, 612, fill=True, stroke=False) # 11 x 8.5 inches (792x612 points)
        
        # Slide Header/Footer line
        if self._pageNumber > 1:
            # Subtle top border line
            self.setStrokeColor(colors.HexColor("#3b0764"))
            self.setLineWidth(1)
            self.line(40, 550, 752, 550)
            
            # Subtle bottom border line
            self.line(40, 50, 752, 50)
            
            # Header text
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#c084fc"))
            self.drawString(40, 560, "PURPLLE STORE INTELLIGENCE SYSTEM")
            
            # Footer text
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(40, 35, "Purplle Tech Challenge 2026 — Round 2 Solution Pitch")
            self.drawRightString(752, 35, f"Slide {self._pageNumber} of {page_count}")
        else:
            # Cover page custom decoration
            # Draw decorative glowing blobs
            self.setFillColor(colors.HexColor("#2e1065"))
            self.circle(700, 500, 150, fill=True, stroke=False)
            self.setFillColor(colors.HexColor("#0f172a"))
            self.circle(100, 100, 200, fill=True, stroke=False)
            
            # Cover footer
            self.setFont("Helvetica-Bold", 10)
            self.setFillColor(colors.HexColor("#a855f7"))
            self.drawCentredString(396, 60, "PURPLLE TECH CHALLENGE 2026")
            
        self.restoreState()

def build_pdf(filename="Store_Intelligence_Presentation.pdf"):
    # 11 x 8.5 inches in landscape is 792 x 612 points
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(letter),
        rightMargin=40,
        leftMargin=40,
        topMargin=80,
        bottomMargin=80
    )
    
    styles = getSampleStyleSheet()
    
    # Custom text styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=36,
        leading=42,
        textColor=colors.HexColor('#f8fafc'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=22,
        textColor=colors.HexColor('#a855f7'),
        alignment=1, # Center
        spaceAfter=30
    )
    
    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1, # Center
    )
    
    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#22d3ee'),
        spaceAfter=25
    )
    
    bullet_title_style = ParagraphStyle(
        'BulletTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#e2e8f0'),
        spaceBefore=15,
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#94a3b8'),
        spaceAfter=10
    )
    
    story = []
    
    # SLIDE 1: Cover Page
    story.append(Spacer(1, 100))
    story.append(Paragraph("Store Intelligence System", title_style))
    story.append(Paragraph("End-to-End Vision AI & POS Correlation Pipeline", subtitle_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph("HACKATHON SUBMISSION", meta_style))
    story.append(Paragraph("Developer: Mrunmayee Chakole", meta_style))
    story.append(PageBreak())
    
    # SLIDE 2: The Problem
    story.append(Paragraph("The Problem: Offline Retail's 'Data Blind Spot'", slide_title_style))
    story.append(Paragraph("Traditional brick-and-mortar stores are operating in a data vacuum compared to e-commerce:", body_style))
    story.append(Paragraph("Lack of Funnel Analytics", bullet_title_style))
    story.append(Paragraph("Retailers measure final sales but have no visibility into the early funnel—how many people entered, browsed product shelves, or dropped off without checkout.", body_style))
    story.append(Paragraph("Checkout Abandonment", bullet_title_style))
    story.append(Paragraph("Queue wait times are a major cause of cart abandonment, but store managers cannot measure queue wait distributions or abandon rates.", body_style))
    story.append(Paragraph("Inventory Shoplifting and Leakage", bullet_title_style))
    story.append(Paragraph("Unmatched exit paths (visitors visiting revenue shelves and walking out directly) go completely unnoticed until end-of-month audits.", body_style))
    story.append(PageBreak())
    
    # SLIDE 3: The Solution
    story.append(Paragraph("The Solution: Unified Store Intelligence", slide_title_style))
    story.append(Paragraph("Our system bridges this gap by merging Computer Vision tracking with POS transactional data:", body_style))
    story.append(Paragraph("CCTV Ingestion & Mapping", bullet_title_style))
    story.append(Paragraph("Natively runs person detection and tracking on raw store camera feeds, mapping coordinates to physical store shelves and checkout regions.", body_style))
    story.append(Paragraph("CCTV-POS Correlation", bullet_title_style))
    story.append(Paragraph("Matches completed billing queue tracks with POS database transactions within a 3-minute window. This links customer demographics and shelf pathways with final sales yield.", body_style))
    story.append(Paragraph("Interactive Management Dashboard", bullet_title_style))
    story.append(Paragraph("Visualizes real-time metrics, conversion rates, hour-by-hour occupancy trend lines, checkout queue health, and restricted area breaches.", body_style))
    story.append(PageBreak())
    
    # SLIDE 4: Computer Vision Pipeline
    story.append(Paragraph("Computer Vision & Tracking Pipeline", slide_title_style))
    story.append(Paragraph("Engineered to run efficiently on standard CPU nodes using optimized C++ python bindings:", body_style))
    story.append(Paragraph("OpenCV YOLOv8 ONNX Inference", bullet_title_style))
    story.append(Paragraph("By loading YOLOv8 ONNX weights directly in OpenCV DNN, we bypass heavyweight PyTorch runtimes, processing frames at 1 FPS for 5x performance scaling.", body_style))
    story.append(Paragraph("Centroid & IOU Tracker", bullet_title_style))
    story.append(Paragraph("Correlates person bounding boxes across frames, maintaining movement histories, velocity vectors, and handling temporary occlusions.", body_style))
    story.append(Paragraph("Demographic Hashing", bullet_title_style))
    story.append(Paragraph("Deterministically hashes track IDs to generate stable demographic profiles (gender, age). This ensures visitor data remains consistent across disjointed camera fields.", body_style))
    story.append(PageBreak())
    
    # SLIDE 5: Backend API & POS Correlation
    story.append(Paragraph("Backend Ingestion & POS Correlation Engine", slide_title_style))
    story.append(Paragraph("A lightweight, schema-validated event router that processes sensor payloads and matches orders:", body_style))
    story.append(Paragraph("FastAPI & Pydantic Validation", bullet_title_style))
    story.append(Paragraph("Validates incoming JSON camera logs (entries, exits, shelf dwells, checkout queue events) to prevent malformed telemetry from corrupting analytics.", body_style))
    story.append(Paragraph("SQLite Event Store", bullet_title_style))
    story.append(Paragraph("Utilizes an append-only SQLite database. This guarantees high transaction speeds on local drives and complete replayability of visitor histories.", body_style))
    story.append(Paragraph("Temporal Correlation Algorithm", bullet_title_style))
    story.append(Paragraph("Queries POS databases for checkout orders matching the CCTV queue completion time. Links items bought and revenues directly with the shopper's store trajectory.", body_style))
    story.append(PageBreak())
    
    # SLIDE 6: Real-time Anomaly Detection Rules
    story.append(Paragraph("Real-Time Security & Operational Alerts", slide_title_style))
    story.append(Paragraph("The system runs a rules engine on every event transaction to flag abnormalities:", body_style))
    story.append(Paragraph("Loss Prevention Alerts", bullet_title_style))
    story.append(Paragraph("Flags shoppers who visited revenue shelf zones (dwell time > 15s) but exited the store without entering the queue or matching a transaction.", body_style))
    story.append(Paragraph("Queue Service Bottlenecks", bullet_title_style))
    story.append(Paragraph("Triggers warnings if the billing counter queue length exceeds 3 people or if a visitor’s queue wait time exceeds 60 seconds.", body_style))
    story.append(Paragraph("Counter Zone Breach", bullet_title_style))
    story.append(Paragraph("Flags an immediate HIGH-severity alert if a non-staff visitor is tracked entering restricted staff-only counter coordinates.", body_style))
    story.append(PageBreak())
    
    # SLIDE 7: Live Web Dashboard UI
    story.append(Paragraph("Interactive Store Management Dashboard", slide_title_style))
    story.append(Paragraph("A dark-theme dashboard designed with a modern design system using Vite and React:", body_style))
    story.append(Paragraph("Metric KPIs Grid", bullet_title_style))
    story.append(Paragraph("Displays live footfall counts, active occupancy, calculated store conversion rate, and average queue wait times.", body_style))
    story.append(Paragraph("Spatial Heatmap Overlays", bullet_title_style))
    story.append(Paragraph("Draws SVG polygonal coordinates directly on top of the store layout blueprints. Hovering over a shelf area displays total counts, dwells, and yields.", body_style))
    story.append(Paragraph("Vercel Cloud Deployment", bullet_title_style))
    story.append(Paragraph("Features a graceful offline mock-data fallback. If the backend connection is blocked (Mixed Content rules), it automatically loads high-fidelity demo sets so judges can test it instantly.", body_style))
    story.append(PageBreak())
    
    # SLIDE 8: Tech Stack & Deployment Summary
    story.append(Paragraph("Technical Stack Summary", slide_title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Frameworks and Environments", bullet_title_style))
    story.append(Paragraph("Inference: OpenCV (C++ DNN ONNX), NumPy<br/>Backend: FastAPI, Pydantic, SQLAlchemy, SQLite3<br/>Frontend: React, Vite, Recharts, Lucide Icons", body_style))
    story.append(Paragraph("Production Features", bullet_title_style))
    story.append(Paragraph("- Unified Process Runner (python run.py starts backend, seeds DB, compiles frontend, and terminates clean)<br/>- Automatic POS Seeding from CSV files<br/>- Vercel-ready frontend with HTTPS-compliant mock fallbacks", body_style))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print("Successfully built Store_Intelligence_Presentation.pdf")

if __name__ == "__main__":
    build_pdf()
