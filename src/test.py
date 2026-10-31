import os
import sys
import json
import cv2
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
                frame = self.frame_queue.get()
                
                # device=0 forces it to use your RTX 4060
                results = self.model.predict(source=frame, verbose=False, conf=0.15, device=0)
                
                detections = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls_id]
                    
                    detections.append({
                        'name': class_name, 
                        'conf': conf, 
                        'box': (x1, y1, x2, y2)
                    })
                
                if not self.result_queue.full():
                    self.result_queue.put((frame, detections))

    def stop(self):
        self.running = False
        self.thread.join()


class ConsecutiveDetectionTracker:
    """
    Verifies that a detected object is genuinely present for at least
    `min_frames` (20) out of `window_size` (30) consecutive frames before
    looking up its shelf life in items_shelf_life.json and logging to inventory.json.
    """

    def __init__(self, shelf_life_db, inventory_manager, window_size=WINDOW_SIZE, min_frames=MIN_CONFIRM_FRAMES):
        self.shelf_life_db = shelf_life_db
        self.inventory_manager = inventory_manager
        self.window_size = window_size
        self.min_frames = min_frames
        self.windows = defaultdict(lambda: deque(maxlen=self.window_size))
        self.logged_active = set()

    def update(self, detections):
        """
        Processes one frame's detections, updates the 30-frame sliding windows,
        and logs newly confirmed items (>= 20/30 frames) to inventory.json.
        Returns a dict mapping canonical_name -> (hits_in_window, is_logged).
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

            # Confirm and log if seen in >= 20 out of 30 consecutive frames
            if hits >= self.min_frames and item_name not in self.logged_active:
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

                    added, _ = self.inventory_manager.add_item(product_details, bypass_cooldown=True)
                    if added:
                        self.inventory_manager.print_item(product_details, is_new=True)
                    self.logged_active.add(item_name)

            # Reset latch once item has completely left the 30-frame window
            elif item_name in self.logged_active and hits == 0:
                self.logged_active.remove(item_name)

            status_map[item_name] = (hits, item_name in self.logged_active)

        return status_map


# --- Testing the Pipeline ---
if __name__ == "__main__":
    # Just type what you want to find in plain English
    TARGET_CLASSES = ["green plastic snack packet", "white egg", "light green banana", "orange carrot", "red tomato", ""]
    
    shelf_life_db = load_items_shelf_life()
    inventory_manager = InventoryManager()
    tracker = ConsecutiveDetectionTracker(
        shelf_life_db=shelf_life_db,
        inventory_manager=inventory_manager,
        window_size=WINDOW_SIZE,
        min_frames=MIN_CONFIRM_FRAMES,
    )

    scanner = YOLOWorldScanner(TARGET_CLASSES)
    cap = cv2.VideoCapture(1) # 0 for webcam, or use smartphone IP camera URL

    print(f"Loaded YOLO-World. Searching for: {TARGET_CLASSES}")
    print(f"Shelf-life catalog loaded: {list(shelf_life_db.keys())}")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            if not scanner.frame_queue.full():
                scanner.frame_queue.put(frame.copy())

            if not scanner.result_queue.empty():
                processed_frame, detections = scanner.result_queue.get()
                status_map = tracker.update(detections)
                
                for det in detections:
                    x1, y1, x2, y2 = det['box']
                    raw_name = det['name']
                    canonical_name = det.get('canonical_name')

                    if canonical_name and canonical_name in status_map:
                        hits, is_logged = status_map[canonical_name]
                        if is_logged:
                            color = (0, 255, 0)  # Green once confirmed & logged
                            label = f"{canonical_name} {det['conf']:.2f} [LOGGED]"
                        else:
                            color = (0, 215, 255)  # Amber while verifying (hits/20)
                            label = f"{canonical_name} {det['conf']:.2f} [{hits}/{MIN_CONFIRM_FRAMES}]"
                    else:
                        color = (180, 180, 180)
                        label = f"{raw_name} {det['conf']:.2f}"
                    
                    # Draw bounding box
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                    # Draw label
                    cv2.putText(processed_frame, label, 
                                (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                cv2.imshow("Zero-Shot Smart Fridge", processed_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        scanner.stop()
        cap.release()
        cv2.destroyAllWindows()
