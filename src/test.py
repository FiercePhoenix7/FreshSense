import os
import sys
import json
import cv2
import numpy as np
import threading
import queue
from collections import defaultdict, deque
from datetime import date, timedelta
from ultralytics import YOLOWorld

# Ensure local modules and project paths are accessible
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from inventory import InventoryManager

SHELF_LIFE_PATH = os.path.join(PROJECT_ROOT, "data", "items_shelf_life.json")
MODEL_PATH = (
    os.path.join(PROJECT_ROOT, "yolov8m-world.pt")
    if os.path.exists(os.path.join(PROJECT_ROOT, "yolov8m-world.pt"))
    else "yolov8m-world.pt"
)

WINDOW_SIZE = 30
MIN_CONFIRM_FRAMES = 20


def load_items_shelf_life(path=SHELF_LIFE_PATH):
    """Loads item shelf-life and category mappings from data/items_shelf_life.json."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ShelfLife] Warning: Could not load {path}: {e}")
    return {}


def match_shelf_life_item(detected_label, shelf_life_db):
    """
    Matches a YOLO-World class prompt (e.g. 'light green banana' or 'Banana')
    against entries in items_shelf_life.json.
    Returns (canonical_name, item_info) or (None, None).
    """
    if not detected_label or not detected_label.strip():
        return None, None

    label_lower = detected_label.strip().lower()

    # 1. Exact case-insensitive match
    for key, info in shelf_life_db.items():
        if key.lower() == label_lower:
            return key, info

    # 2. Substring match (e.g., 'banana' in 'light green banana')
    for key, info in shelf_life_db.items():
        key_lower = key.lower()
        if key_lower in label_lower or label_lower in key_lower:
            return key, info

    return None, None


class YOLOWorldScanner:
    def __init__(self, target_classes):
        # yolov8s-world.pt (Small) is a great balance of speed and accuracy
        # yolov8m-world.pt (Medium) is available if you need more accuracy
        self.model = YOLOWorld(MODEL_PATH)
        
        # Set custom vocabulary for zero-shot detection
        self.model.set_classes(target_classes)
        
        self.frame_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=2)
        self.running = True
        
        self.thread = threading.Thread(target=self._run_inference, daemon=True)
        self.thread.start()

    def _run_inference(self):
        while self.running:
            if not self.frame_queue.empty():
                item = self.frame_queue.get()
                if isinstance(item, tuple):
                    display_frame, detect_frame, left_mask = item
                else:
                    display_frame, detect_frame, left_mask = item, item, None
                
                # device=0 forces it to use your RTX 4060
                results = self.model.predict(source=detect_frame, verbose=False, conf=0.15, device=0)
                
                detections = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    if left_mask is not None:
                        cx = min(max((x1 + x2) // 2, 0), left_mask.shape[1] - 1)
                        cy = min(max((y1 + y2) // 2, 0), left_mask.shape[0] - 1)
                        if not left_mask[cy, cx]:
                            continue

                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls_id]
                    
                    detections.append({
                        'name': class_name, 
                        'conf': conf, 
                        'box': (x1, y1, x2, y2)
                    })
                
                if not self.result_queue.full():
                    self.result_queue.put((display_frame, detections))

    def stop(self):
        self.running = False
        self.thread.join()


class ConsecutiveDetectionTracker:
    """
    Verifies that a detected object is genuinely present for at least
    `min_frames` (20) out of `window_size` (30) consecutive frames before
    looking up its shelf life in items_shelf_life.json and either logging to
    or removing from inventory.json depending on the active mode ('INSERT' or 'REMOVE').
    """

    def __init__(self, shelf_life_db, inventory_manager, window_size=WINDOW_SIZE, min_frames=MIN_CONFIRM_FRAMES):
        self.shelf_life_db = shelf_life_db
        self.inventory_manager = inventory_manager
        self.window_size = window_size
        self.min_frames = min_frames
        self.mode = "INSERT"  # 'INSERT' or 'REMOVE'
        self.windows = defaultdict(lambda: deque(maxlen=self.window_size))
        self.processed_active = {}  # item_name -> action status tag ('LOGGED', 'REMOVED', 'NOT IN INV')

    def set_mode(self, mode):
        """Switches between 'INSERT' and 'REMOVE' modes and resets active tracking windows."""
        if mode in ("INSERT", "REMOVE") and mode != self.mode:
            self.mode = mode
            self.windows.clear()
            self.processed_active.clear()
            self.inventory_manager.reset_cooldowns()
            print(f"[SmartFridge] Switched to {self.mode} mode", flush=True)

    def update(self, detections):
        """
        Processes one frame's detections, updates the 30-frame sliding windows,
        and logs or removes newly confirmed items (>= 20/30 frames) in inventory.json.
        Returns a dict mapping canonical_name -> (hits_in_window, status_tag_or_None).
        """
        present_canonical = set()
        for det in detections:
            canonical_name, _ = match_shelf_life_item(det.get("name", ""), self.shelf_life_db)
            if canonical_name:
                present_canonical.add(canonical_name)
                det["canonical_name"] = canonical_name

        tracked_keys = set(self.windows.keys()) | present_canonical | set(self.shelf_life_db.keys())
        status_map = {}

        for item_name in tracked_keys:
            is_present = 1 if item_name in present_canonical else 0
            window = self.windows[item_name]
            window.append(is_present)
            hits = sum(window)

            # Confirm and execute action if seen in >= 20 out of 30 consecutive frames
            if hits >= self.min_frames and item_name not in self.processed_active:
                info = self.shelf_life_db.get(item_name)
                if info:
                    shelf_days = int(info.get("shelf_life", 7))
                    category = info.get("category", "General")
                    today = date.today()
                    expiry_date = (today + timedelta(days=shelf_days)).strftime("%Y-%m-%d")

                    if shelf_days < 0:
                        status = "Expired"
                    elif shelf_days <= 3:
                        status = "Expiring Soon"
                    else:
                        status = "Fresh"

                    product_details = {
                        "name": item_name,
                        "category": category,
                        "expiry_date": expiry_date,
                        "days_until_expiry": shelf_days,
                        "status": status,
                    }

                    if self.mode == "INSERT":
                        added, _ = self.inventory_manager.add_item(product_details, bypass_cooldown=True)
                        if added:
                            self.inventory_manager.print_item(product_details, is_new=True)
                        self.processed_active[item_name] = "LOGGED"
                    else:
                        removed, result = self.inventory_manager.remove_item(product_details, bypass_cooldown=True)
                        if removed:
                            self.inventory_manager.print_removal(result, success=True)
                            self.processed_active[item_name] = "REMOVED"
                        else:
                            self.inventory_manager.print_removal(product_details, success=False)
                            self.processed_active[item_name] = "NOT IN INV"

            # Reset latch once item has completely left the 30-frame window
            elif item_name in self.processed_active and hits == 0:
                del self.processed_active[item_name]

            status_map[item_name] = (hits, self.processed_active.get(item_name))

        return status_map


def build_left_of_line_mask(frame_shape, pt1, pt2):
    """
    Given two clicked points pt1=(x1, y1) and pt2=(x2, y2), builds a boolean mask
    that is True for all pixels to the left of the line passing through pt1 and pt2,
    along with the line's full-frame endpoints for drawing.
    """
    h, w = frame_shape[:2]
    # Order points top-to-bottom so "left of the line" is always unambiguous
    if pt1[1] <= pt2[1]:
        (x_a, y_a), (x_b, y_b) = pt1, pt2
    else:
        (x_a, y_a), (x_b, y_b) = pt2, pt1

    yy, xx = np.ogrid[:h, :w]
    if y_b != y_a:
        slope = (x_b - x_a) / float(y_b - y_a)
        x_on_line = x_a + (yy - y_a) * slope
        left_mask = xx <= x_on_line
        line_start = (int(round(x_a + (0 - y_a) * slope)), 0)
        line_end = (int(round(x_a + ((h - 1) - y_a) * slope)), h - 1)
    else:
        cutoff_x = max(x_a, x_b)
        left_mask = xx <= cutoff_x
        line_start = (cutoff_x, 0)
        line_end = (cutoff_x, h - 1)

    return left_mask, line_start, line_end


# --- Testing the Pipeline ---
if __name__ == "__main__":
    # Just type what you want to find in plain English
    TARGET_CLASSES = ["white egg", "light green banana", "orange carrot", "red tomato", ""]
    
    shelf_life_db = load_items_shelf_life()
    inventory_manager = InventoryManager()
    tracker = ConsecutiveDetectionTracker(
        shelf_life_db=shelf_life_db,
        inventory_manager=inventory_manager,
        window_size=WINDOW_SIZE,
        min_frames=MIN_CONFIRM_FRAMES,
    )

    scanner = YOLOWorldScanner(TARGET_CLASSES)
    cap = cv2.VideoCapture(0) # 0 for webcam, or use smartphone IP camera URL

    WINDOW_NAME = "Zero-Shot Smart Fridge"
    cv2.namedWindow(WINDOW_NAME)

    line_points = []
    left_mask = None
    line_endpoints = None

    def on_mouse(event, x, y, flags, param):
        global line_points, left_mask, line_endpoints
        if event == cv2.EVENT_LBUTTONDOWN and len(line_points) < 2:
            line_points.append((x, y))
            print(f"[Boundary] Point {len(line_points)} selected at ({x}, {y})", flush=True)

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    print(f"Loaded YOLO-World. Searching for: {TARGET_CLASSES}")
    print(f"Shelf-life catalog loaded: {list(shelf_life_db.keys())}")
    print("Step 1: Click 2 points in the camera window to set the scan boundary line (left of line is scanned).")
    print("Controls: 'i' = Insert mode | 'r' = Remove mode | 'c' = Re-pick boundary line | 'q' = Quit")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            # Calibration phase: wait until user clicks 2 points to define the line
            if len(line_points) < 2:
                preview = frame.copy()
                for pt in line_points:
                    cv2.circle(preview, pt, 6, (0, 255, 255), -1)
                cv2.putText(
                    preview,
                    f"Click 2 points for boundary line ({len(line_points)}/2)",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 255),
                    2,
                )
                cv2.imshow(WINDOW_NAME, preview)
            else:
                # Build mask once when the 2nd point is clicked
                if left_mask is None:
                    left_mask, l_start, l_end = build_left_of_line_mask(
                        frame.shape, line_points[0], line_points[1]
                    )
                    line_endpoints = (l_start, l_end)
                    print("[Boundary] Line calibrated! Scanning region to the left of the line.", flush=True)

                if not scanner.frame_queue.full():
                    # Mask out everything to the right of the line before sending for detection
                    masked_frame = np.zeros_like(frame)
                    masked_frame[left_mask] = frame[left_mask]
                    scanner.frame_queue.put((frame.copy(), masked_frame, left_mask))

                if not scanner.result_queue.empty():
                    processed_frame, detections = scanner.result_queue.get()
                    status_map = tracker.update(detections)

                    # Draw the boundary line
                    if line_endpoints is not None:
                        cv2.line(processed_frame, line_endpoints[0], line_endpoints[1], (255, 255, 0), 2)
                    
                    for det in detections:
                        x1, y1, x2, y2 = det['box']
                        raw_name = det['name']
                        canonical_name = det.get('canonical_name')

                        if canonical_name and canonical_name in status_map:
                            hits, action_tag = status_map[canonical_name]
                            if action_tag == "LOGGED":
                                color = (0, 255, 0)      # Green once confirmed & logged
                                label = f"{canonical_name} {det['conf']:.2f} [LOGGED]"
                            elif action_tag == "REMOVED":
                                color = (0, 0, 255)      # Red once confirmed & removed
                                label = f"{canonical_name} {det['conf']:.2f} [REMOVED]"
                            elif action_tag == "NOT IN INV":
                                color = (0, 140, 255)    # Orange if not found in inventory
                                label = f"{canonical_name} {det['conf']:.2f} [NOT IN INV]"
                            else:
                                color = (0, 215, 255)    # Amber while verifying (hits/20)
                                label = f"{canonical_name} {det['conf']:.2f} [{hits}/{MIN_CONFIRM_FRAMES}]"
                        else:
                            color = (180, 180, 180)
                            label = f"{raw_name} {det['conf']:.2f}"
                        
                        # Draw bounding box
                        cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                        # Draw label
                        cv2.putText(processed_frame, label, 
                                    (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    # Draw small 'I' or 'R' mode indicator at the top right
                    h, w = processed_frame.shape[:2]
                    mode_letter = "I" if tracker.mode == "INSERT" else "R"
                    mode_color = (0, 255, 0) if tracker.mode == "INSERT" else (0, 0, 255)
                    cv2.putText(
                        processed_frame,
                        mode_letter,
                        (w - 35, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        mode_color,
                        2,
                    )
                    
                    cv2.imshow(WINDOW_NAME, processed_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in (ord('r'), ord('R')):
                tracker.set_mode("REMOVE")
            elif key in (ord('i'), ord('I')):
                tracker.set_mode("INSERT")
            elif key in (ord('c'), ord('C')):
                line_points.clear()
                left_mask = None
                line_endpoints = None
                tracker.windows.clear()
                tracker.processed_active.clear()
                print("[Boundary] Cleared boundary line. Click 2 points to re-calibrate.", flush=True)
    finally:
        scanner.stop()
        cap.release()
        cv2.destroyAllWindows()
