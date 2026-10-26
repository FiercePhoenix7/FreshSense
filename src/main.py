import os
import sys
import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode

# Ensure local modules can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from product_lookup import ProductLookupService
from inventory import InventoryManager

class FreshSenseScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("FreshSense - Layer 1 Barcode Recognition & Inventory")
        self.root.geometry("760x730")
        self.root.configure(bg="#f5f6f8")
        
        # --- Services Setup ---
        self.product_lookup = ProductLookupService()
        self.inventory_manager = InventoryManager()
        
        # --- UI Setup ---
        self.header_label = tk.Label(
            root, 
            text="FreshSense Fridge Entry Scanner", 
            font=("Arial", 18, "bold"),
            bg="#f5f6f8",
            fg="#1a1a1a"
        )
        self.header_label.pack(pady=(12, 6))
        
        self.subtitle_label = tk.Label(
            root, 
            text="Present packaged item barcode to camera to register product & expiry", 
            font=("Arial", 10),
            bg="#f5f6f8",
            fg="#666666"
        )
        self.subtitle_label.pack(pady=(0, 10))
        
        # Video Frame container
        self.video_container = tk.Frame(root, bg="#000000", bd=2, relief=tk.GROOVE)
        self.video_container.pack()
        
        self.video_label = tk.Label(self.video_container, bg="#000000")
        self.video_label.pack()
        
        # Product Identification & Expiry Result Card
        self.card_frame = tk.Frame(root, bg="#ffffff", bd=1, relief=tk.RIDGE, padx=16, pady=12)
        self.card_frame.pack(fill=tk.X, padx=30, pady=14)
        
        self.card_title = tk.Label(
            self.card_frame, 
            text="Waiting for item...", 
            font=("Arial", 14, "bold"), 
            bg="#ffffff", 
            fg="#f57c00"
        )
        self.card_title.pack(anchor=tk.W)
        
        self.card_expiry = tk.Label(
            self.card_frame, 
            text="Hold a barcode inside the guide box", 
            font=("Arial", 12), 
            bg="#ffffff", 
            fg="#555555"
        )
        self.card_expiry.pack(anchor=tk.W, pady=(4, 2))
        
        self.card_meta = tk.Label(
            self.card_frame, 
            text="Inventory status: Ready", 
            font=("Arial", 10), 
            bg="#ffffff", 
            fg="#888888"
        )
        self.card_meta.pack(anchor=tk.W)
        
        # --- Camera Setup ---
        # Adjust camera index (e.g., 0, 1, or 2 depending on your setup)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Performance trackers
        self.frame_count = 0
        self.scan_interval = 3  # Decode every 3rd frame to keep FPS buttery smooth
        self.last_barcode_data = None
        
        self.update_frame()
        
    def _update_ui_display(self, product, barcode_type, is_new=True):
        """Updates the Tkinter UI card with product details and expiry."""
        name = product.get("name", "Unknown Product")
        brand = product.get("brand", "Unknown")
        category = product.get("category", "General")
        barcode = product.get("barcode")
        expiry = product.get("expiry_date")
        days = product.get("days_until_expiry", 0)
        status = product.get("status", "Fresh")
        
        # Status color
        if status == "Fresh":
            status_color = "#2e7d32"  # Green
            days_text = f"{days} days remaining"
        elif status == "Expiring Soon":
            status_color = "#e65100"  # Orange
            days_text = f"Only {days} day(s) left!"
        else:
            status_color = "#c62828"  # Red
            days_text = f"EXPIRED ({abs(days)} days ago)"
            
        self.card_title.config(
            text=f"{name}", 
            fg=status_color
        )
        
        self.card_expiry.config(
            text=f"Expiry Date: {expiry}  •  Status: {status} ({days_text})",
            fg=status_color
        )
        
        inventory_msg = "✓ Logged to inventory" if is_new else "✓ Already in inventory"
        self.card_meta.config(
            text=f"Category: {category}  |  Brand: {brand}  |  Code: {barcode} ({barcode_type})  |  {inventory_msg}",
            fg="#555555"
        )

    def update_frame(self):
        ret, frame = self.cap.read()
        
        if ret:
            self.frame_count += 1
            h, w, _ = frame.shape
            
            # 1. Define a central Region of Interest (ROI) box
            roi_w, roi_h = int(w * 0.6), int(h * 0.5)
            roi_x = int((w - roi_w) / 2)
            roi_y = int((h - roi_h) / 2)
            
            # Crop the ROI and convert to single-channel grayscale
            roi_crop = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
            gray_roi = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
            
            # 2. Run barcode detection only on throttled frames
            if self.frame_count % self.scan_interval == 0:
                barcodes = decode(gray_roi)
                
                if barcodes:
                    for barcode in barcodes:
                        data = barcode.data.decode('utf-8')
                        b_type = barcode.type
                        
                        # Translate ROI local coords to the global frame coords
                        bx, by, bw, bh = barcode.rect
                        abs_x, abs_y = roi_x + bx, roi_y + by
                        
                        # Look up product info and calculate expiry
                        product = self.product_lookup.lookup(data)
                        
                        # Draw green bounding box around detected code
                        cv2.rectangle(frame, (abs_x, abs_y), (abs_x + bw, abs_y + bh), (0, 255, 0), 3)
                        
                        # Overlay product name & expiry above barcode box
                        overlay_text = f"{product['name'][:22]} | Exp: {product['expiry_date']}"
                        cv2.putText(
                            frame, 
                            overlay_text, 
                            (abs_x, max(abs_y - 12, 30)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.7, 
                            (0, 255, 0), 
                            2
                        )
                        
                        # Add item to inventory and print details to console
                        is_new, _ = self.inventory_manager.add_item(product)
                        if is_new:
                            self.inventory_manager.print_item(product, is_new=True)
                            self._update_ui_display(product, b_type, is_new=True)
                        elif data != self.last_barcode_data:
                            self._update_ui_display(product, b_type, is_new=False)
                            
                        self.last_barcode_data = data
                else:
                    # Draw a subtle viewfinder box to guide where to present the item
                    cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (200, 200, 200), 2)
            else:
                # Keep guide visible on non-scanned frames
                cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (200, 200, 200), 2)
            
            # 3. Downscale preview cleanly for Tkinter display
            display_frame = cv2.resize(frame, (640, 360))
            cv2image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        # Schedule next tick quickly (~60fps target loop)
        self.root.after(10, self.update_frame)
        
    def on_closing(self):
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FreshSenseScanner(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

    root.mainloop()