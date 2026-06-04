import cv2
import numpy as np
import os

class YOLODetector:
    def __init__(self, model_path="yolov8n.onnx", conf_threshold=0.35, nms_threshold=0.45):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ONNX model file not found at: {model_path}")
            
        self.net = cv2.dnn.readNetFromONNX(model_path)
        # Enable GPU if available (we default to CPU but setup configuration)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def detect_persons(self, frame):
        """
        Runs object detection on a frame and filters for 'person' class.
        Returns list of bounding boxes: [[x, y, w, h], ...] and list of confidences.
        """
        H, W = frame.shape[:2]
        # YOLOv8 expects 640x640 input
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()[0]
        
        # Scaling factors
        x_scale = W / 640
        y_scale = H / 640
        
        boxes = []
        confidences = []
        
        # Parse detections (transposing output to iterate rows)
        for row in out.T:
            conf = float(row[4])  # Person is the first class (idx 4 in 84 features)
            if conf > self.conf_threshold:
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                x = int((cx - w/2) * x_scale)
                y = int((cy - h/2) * y_scale)
                box_w = int(w * x_scale)
                box_h = int(h * y_scale)
                
                # Prevent negative or out of bounds coordinates
                x = max(0, x)
                y = max(0, y)
                box_w = min(W - x, box_w)
                box_h = min(H - y, box_h)
                
                boxes.append([x, y, box_w, box_h])
                confidences.append(conf)
                
        # Apply Non-Maximum Suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)
        
        final_boxes = []
        final_confs = []
        
        if len(indices) > 0:
            for idx in (indices.flatten() if hasattr(indices, 'flatten') else indices):
                final_boxes.append(boxes[idx])
                final_confs.append(confidences[idx])
                
        return final_boxes, final_confs
