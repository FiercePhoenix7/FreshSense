import os
import sys
import json
import time
import cv2
import numpy as np
import threading
import queue
from collections import defaultdict, deque
from datetime import date, timedelta
from pyzbar.pyzbar import decode as decode_barcodes
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
PRODUCTS_PATH = os.path.join(PROJECT_ROOT, "data", "products.json")
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


def load_products_catalog(path=PRODUCTS_PATH):
    """Loads barcode product catalog from data/products.json."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Products] Warning: Could not load {path}: {e}")
    return {}


def lookup_barcode_product(barcode_str, products_db=None, path=PRODUCTS_PATH):
    """
    Looks up `barcode_str` in data/products.json and computes expiry details.
    Returns a product_details dict with 'barcode', 'name', 'category',
    'expiry_date', 'days_until_expiry', and 'status', or None if not found.
    """
    barcode_clean = str(barcode_str).strip()
    if not barcode_clean:
        return None

    catalog = products_db if products_db is not None else load_products_catalog(path)
    info = catalog.get(barcode_clean)

    # Try matching without leading zeros if not an exact match
    if info is None:
        stripped = barcode_clean.lstrip("0")
        for key, val in catalog.items():
            if str(key).strip().lstrip("0") == stripped:
                info = val
                break

    # Reload from disk once in case products.json was updated while running
    if info is None and products_db is not None:
        fresh_catalog = load_products_catalog(path)
        products_db.clear()
        products_db.update(fresh_catalog)
        info = products_db.get(barcode_clean)
        if info is None:
            stripped = barcode_clean.lstrip("0")
            for key, val in products_db.items():
                if str(key).strip().lstrip("0") == stripped:
                    info = val
                    break

    if info is None:
        return None

    name = info.get("name", "Unknown Product")
    category = info.get("category", "General")
    shelf_days = int(info.get("shelf_life_days", info.get("shelf_life", 7)))
    today = date.today()
    expiry_date = (today + timedelta(days=shelf_days)).strftime("%Y-%m-%d")

    if shelf_days < 0:
        status = "Expired"
    elif shelf_days <= 3:
        status = "Expiring Soon"
    else:
        status = "Fresh"

    return {
        "barcode": barcode_clean,
        "name": name,
        "category": category,
        "expiry_date": expiry_date,
        "days_until_expiry": shelf_days,
        "status": status,
    }


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
                scan_mode = "CV"
                if isinstance(item, tuple):
                    if len(item) == 4:
                        display_frame, detect_frame, left_mask, scan_mode = item
                    else:
                        display_frame, detect_frame, left_mask = item
                else:
                    display_frame, detect_frame, left_mask = item, item, None

                detections = []
                if scan_mode == "BARCODE":
                    gray = cv2.cvtColor(detect_frame, cv2.COLOR_BGR2GRAY)
                    barcodes = decode_barcodes(gray)
                    for b in barcodes:
                        bx, by, bw, bh = b.rect
                        x1, y1, x2, y2 = int(bx), int(by), int(bx + bw), int(by + bh)
                        if left_mask is not None:
                            cx = min(max((x1 + x2) // 2, 0), left_mask.shape[1] - 1)
                            cy = min(max((y1 + y2) // 2, 0), left_mask.shape[0] - 1)
                            if not left_mask[cy, cx]:
                                continue
                        barcode_str = b.data.decode("utf-8", errors="ignore").strip()
                        if barcode_str:
                            detections.append({
                                "barcode": barcode_str,
                                "box": (x1, y1, x2, y2),
                            })
                else:
                    # device=0 forces it to use your RTX 4060
                    results = self.model.predict(source=detect_frame, verbose=False, conf=0.15, device=0)
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
                            "name": class_name,
                            "conf": conf,
                            "box": (x1, y1, x2, y2),
                        })

                if not self.result_queue.full():
                    self.result_queue.put((display_frame, scan_mode, detections))

    def clear_queues(self):
        """Drains pending frames and results when switching scan modes."""
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self.running = False
        self.thread.join()


class ConsecutiveDetectionTracker:
    """
    Verifies that a detected object is genuinely present for at least
    `min_frames` (20) out of `window_size` (30) consecutive frames before
    looking up its shelf life in items_shelf_life.json and either logging to
    or removing from inventory.json depending on the active mode ('INSERT' or 'REMOVE').
    Also handles barcode-based Insert/Remove against products.json and inventory.json.
    """

    def __init__(self, shelf_life_db, products_db, inventory_manager, window_size=WINDOW_SIZE, min_frames=MIN_CONFIRM_FRAMES):
        self.shelf_life_db = shelf_life_db
        self.products_db = products_db
        self.inventory_manager = inventory_manager
        self.window_size = window_size
        self.min_frames = min_frames
        self.mode = "INSERT"  # 'INSERT' or 'REMOVE'
        self.windows = defaultdict(lambda: deque(maxlen=self.window_size))
        self.processed_active = {}  # item_name -> action status tag ('LOGGED', 'REMOVED', 'NOT IN INV')
        self.barcode_state = {}     # barcode -> (action_tag, display_name, last_seen_ts)

    def reset_tracking(self):
        """Clears active tracking windows and barcode latches."""
        self.windows.clear()
        self.processed_active.clear()
        self.barcode_state.clear()
        self.inventory_manager.reset_cooldowns()

    def set_mode(self, mode):
        """Switches between 'INSERT' and 'REMOVE' modes and resets active tracking windows."""
        if mode in ("INSERT", "REMOVE") and mode != self.mode:
            self.mode = mode
            self.reset_tracking()
            print(f"[SmartFridge] Switched to {self.mode} mode", flush=True)

    def process_barcodes(self, barcode_detections):
        """
        Processes detected barcodes in BARCODE mode:
        - INSERT ('I'): If barcode is not already in inventory.json, looks up barcode in
          products.json and adds it to inventory.json (with barcode field).
        - REMOVE ('R'): If barcode is in inventory.json, removes it from inventory.json.
        Returns a list of overlay dicts: [{'box': (x1, y1, x2, y2), 'label': str, 'color': tuple}].
        """
        now = time.time()
        # Expire barcode latches that haven't been seen for >2.5 seconds
        expired_keys = [
            bc for bc, (_, _, last_ts) in self.barcode_state.items()
            if (now - last_ts) > 2.5
        ]
        for bc in expired_keys:
            del self.barcode_state[bc]

        overlays = []
        for det in barcode_detections:
            barcode_str = str(det.get("barcode", "")).strip()
            box = det["box"]
            if not barcode_str:
                continue

            if self.mode == "INSERT":
                # Check if barcode is already present in inventory.json
                if self.inventory_manager.has_barcode(barcode_str):
                    prod = lookup_barcode_product(barcode_str, self.products_db)
                    name = prod["name"] if prod else barcode_str
                    self.barcode_state[barcode_str] = ("LOGGED", name, now)
                    overlays.append({
                        "box": box,
                        "label": f"{name} [LOGGED]",
                        "color": (0, 255, 0),
                    })
                else:
                    # Not in inventory.json -> look up in products.json
                    product_details = lookup_barcode_product(barcode_str, self.products_db)
                    if product_details:
                        added, _ = self.inventory_manager.add_item(product_details, bypass_cooldown=True)
                        if added:
                            self.inventory_manager.print_item(product_details, is_new=True)
                        name = product_details["name"]
                        self.barcode_state[barcode_str] = ("LOGGED", name, now)
                        overlays.append({
                            "box": box,
                            "label": f"{name} [LOGGED]",
                            "color": (0, 255, 0),
                        })
                    else:
                        if barcode_str not in self.barcode_state:
                            print(f"[Barcode] Barcode {barcode_str} not found in products.json", flush=True)
                        self.barcode_state[barcode_str] = ("UNKNOWN", barcode_str, now)
                        overlays.append({
                            "box": box,
                            "label": f"{barcode_str} [NOT IN PRODUCTS]",
                            "color": (0, 140, 255),
                        })
            else:
                # REMOVE mode
                if self.inventory_manager.has_barcode(barcode_str):
                    product_details = lookup_barcode_product(barcode_str, self.products_db) or {
                        "barcode": barcode_str,
                        "name": barcode_str,
                        "category": "General",
                    }
                    removed, result = self.inventory_manager.remove_item(product_details, bypass_cooldown=True)
                    if removed:
                        self.inventory_manager.print_removal(result, success=True)
                        name = result.get("name", product_details["name"])
                        self.barcode_state[barcode_str] = ("REMOVED", name, now)
                        overlays.append({
                            "box": box,
                            "label": f"{name} [REMOVED]",
                            "color": (0, 0, 255),
                        })
                else:
                    # If just removed or already checked while still in view, keep showing that status
                    if barcode_str in self.barcode_state:
                        tag, name, _ = self.barcode_state[barcode_str]
                        self.barcode_state[barcode_str] = (tag, name, now)
                    else:
                        product_details = lookup_barcode_product(barcode_str, self.products_db) or {
                            "barcode": barcode_str,
                            "name": barcode_str,
                            "category": "General",
                        }
                        self.inventory_manager.print_removal(product_details, success=False)
                        name = product_details["name"]
                        tag = "NOT IN INV"
                        self.barcode_state[barcode_str] = (tag, name, now)

                    color = (0, 0, 255) if tag == "REMOVED" else (0, 140, 255)
                    overlays.append({
                        "box": box,
                        "label": f"{name} [{tag}]",
                        "color": color,
                    })

        return overlays

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
    Given two clicked points pt1=(x1, y1) and pt2=(x2, y2):
    1. Finds the rightmost point x-coordinate (`crop_x`) so the frame can be cropped
       from the right up to `crop_x`.
    2. Builds a boolean mask of shape (h, crop_x) that masks out the remaining wedge
       to the right of the line connecting the rightmost point and the 2nd point.
    Returns (cropped_left_mask, crop_x, line_start, line_end).
    """
    h, w = frame_shape[:2]
    crop_x = min(w, max(1, max(pt1[0], pt2[0])))

    # Order points top-to-bottom so "left of the line" is always unambiguous
    if pt1[1] <= pt2[1]:
        (x_a, y_a), (x_b, y_b) = pt1, pt2
    else:
        (x_a, y_a), (x_b, y_b) = pt2, pt1

    yy, xx = np.ogrid[:h, :crop_x]
    if y_b != y_a:
        slope = (x_b - x_a) / float(y_b - y_a)
        x_on_line = x_a + (yy - y_a) * slope
        cropped_left_mask = xx <= x_on_line
        line_start = (int(round(x_a + (0 - y_a) * slope)), 0)
        line_end = (int(round(x_a + ((h - 1) - y_a) * slope)), h - 1)
    else:
        cropped_left_mask = np.ones((h, crop_x), dtype=bool)
        line_start = (crop_x, 0)
        line_end = (crop_x, h - 1)

    return cropped_left_mask, crop_x, line_start, line_end


# --- Testing the Pipeline ---
if __name__ == "__main__":
    # Just type what you want to find in plain English
    TARGET_CLASSES = ["white egg", "light green banana", "orange carrot", "red tomato", ""]
    
    shelf_life_db = load_items_shelf_life()
    products_db = load_products_catalog()
    inventory_manager = InventoryManager()
    tracker = ConsecutiveDetectionTracker(
        shelf_life_db=shelf_life_db,
        products_db=products_db,
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
    crop_x = None
    line_endpoints = None
    scan_mode = "CV"  # 'CV' (Computer Vision) or 'BARCODE'
    last_barcode_overlays = []
    barcode_overlay_until = 0.0

    def on_mouse(event, x, y, flags, param):
        global line_points, left_mask, crop_x, line_endpoints
        if event == cv2.EVENT_LBUTTONDOWN and len(line_points) < 2:
            line_points.append((x, y))
            print(f"[Boundary] Point {len(line_points)} selected at ({x}, {y})", flush=True)

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    print(f"Loaded YOLO-World. Searching for: {TARGET_CLASSES}")
    print(f"Shelf-life catalog loaded: {list(shelf_life_db.keys())}")
    print(f"Products barcode catalog loaded: {list(products_db.keys())}")
    print("Step 1: Click 2 points in the camera window to set the scan boundary line (left of line is scanned).")
    print("Controls: 'b' = Toggle CV/Barcode | 'i' = Insert mode | 'r' = Remove mode | 'c' = Re-pick boundary line | 'q' = Quit")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            # Calibration phase: wait until user clicks 2 points to define the line
            if len(line_points) < 2:
                preview = frame.copy()
                for pt in line_points:
                    cv2.circle(preview, pt, 6, (0, 255, 255), -1)
                cv2.imshow(WINDOW_NAME, preview)
            else:
                # Build crop width & mask once when the 2nd point is clicked
                if left_mask is None:
                    left_mask, crop_x, l_start, l_end = build_left_of_line_mask(
                        frame.shape, line_points[0], line_points[1]
                    )
                    line_endpoints = (l_start, l_end)
                    print(f"[Boundary] Line calibrated! Cropping frame width to {crop_x}px and masking to 2nd point.", flush=True)

                if not scanner.frame_queue.full():
                    # 1. Crop frame from the right up to the rightmost point (crop_x)
                    cropped_frame = frame[:, :crop_x].copy()
                    # 2. Mask out the remaining wedge to the right of the line up to the 2nd point
                    cropped_frame[~left_mask] = 0
                    scanner.frame_queue.put((frame.copy(), cropped_frame, left_mask, scan_mode))

                if not scanner.result_queue.empty():
                    processed_frame, result_mode, detections = scanner.result_queue.get()

                    # Draw the boundary line
                    if line_endpoints is not None:
                        cv2.line(processed_frame, line_endpoints[0], line_endpoints[1], (255, 255, 0), 2)

                    if result_mode == "BARCODE":
                        overlays = tracker.process_barcodes(detections)
                        now = time.time()
                        if overlays:
                            last_barcode_overlays = overlays
                            barcode_overlay_until = now + 0.45
                        elif now < barcode_overlay_until:
                            overlays = last_barcode_overlays

                        for ov in overlays:
                            x1, y1, x2, y2 = ov["box"]
                            color = ov["color"]
                            label = ov["label"]
                            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(
                                processed_frame,
                                label,
                                (x1, max(y1 - 10, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                color,
                                2,
                            )
                    else:
                        status_map = tracker.update(detections)

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

                    # Draw small 'C' or 'B' scan mode indicator at the top left
                    h, w = processed_frame.shape[:2]
                    scan_letter = "C" if scan_mode == "CV" else "B"
                    scan_color = (255, 255, 0) if scan_mode == "CV" else (0, 255, 255)
                    cv2.putText(
                        processed_frame,
                        scan_letter,
                        (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        scan_color,
                        2,
                    )

                    # Draw small 'I' or 'R' mode indicator at the top right
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
            elif key in (ord('b'), ord('B')):
                scan_mode = "BARCODE" if scan_mode == "CV" else "CV"
                scanner.clear_queues()
                tracker.reset_tracking()
                last_barcode_overlays.clear()
                barcode_overlay_until = 0.0
                mode_label = "BARCODE" if scan_mode == "BARCODE" else "COMPUTER VISION"
                print(f"[SmartFridge] Switched to {mode_label} mode", flush=True)
            elif key in (ord('r'), ord('R')):
                tracker.set_mode("REMOVE")
                last_barcode_overlays.clear()
                barcode_overlay_until = 0.0
            elif key in (ord('i'), ord('I')):
                tracker.set_mode("INSERT")
                last_barcode_overlays.clear()
                barcode_overlay_until = 0.0
            elif key in (ord('c'), ord('C')):
                line_points.clear()
                left_mask = None
                crop_x = None
                line_endpoints = None
                tracker.reset_tracking()
                last_barcode_overlays.clear()
                barcode_overlay_until = 0.0
                print("[Boundary] Cleared boundary line. Click 2 points to re-calibrate.", flush=True)
    finally:
        scanner.stop()
        cap.release()
        cv2.destroyAllWindows()
