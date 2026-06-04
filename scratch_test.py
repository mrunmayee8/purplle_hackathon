import cv2
import numpy as np

def run():
    cap = cv2.VideoCapture('Store 1/CAM 3 - entry.mp4')
    net = cv2.dnn.readNetFromONNX('yolov8n.onnx')
    
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    x_scale = W / 640
    y_scale = H / 640
    
    frame_idx = 0
    found_dets = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Check every 100 frames to find a person
        if frame_idx % 100 == 0:
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
            net.setInput(blob)
            out = net.forward()[0]
            
            boxes, confs = [], []
            for row in out.T:
                conf = float(row[4])
                if conf > 0.35:
                    # box coordinates: center_x, center_y, width, height
                    cx, cy, w, h = row[0], row[1], row[2], row[3]
                    x = int((cx - w/2) * x_scale)
                    y = int((cy - h/2) * y_scale)
                    box_w = int(w * x_scale)
                    box_h = int(h * y_scale)
                    boxes.append([x, y, box_w, box_h])
                    confs.append(conf)
            
            indices = cv2.dnn.NMSBoxes(boxes, confs, 0.35, 0.45)
            num_dets = len(indices.flatten() if hasattr(indices, 'flatten') else indices)
            
            if num_dets > 0:
                print(f"Frame {frame_idx}: Found {num_dets} detections!")
                # Draw boxes
                for i in (indices.flatten() if hasattr(indices, 'flatten') else indices):
                    x, y, w, h = boxes[i]
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.putText(frame, f"Person: {confs[i]:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                cv2.imwrite('test_det.jpg', frame)
                print(f"Saved test_det.jpg at frame {frame_idx}")
                found_dets += 1
                if found_dets >= 5:
                    break
        
        frame_idx += 1
        
    cap.release()

if __name__ == '__main__':
    run()
