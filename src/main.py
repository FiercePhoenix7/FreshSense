import os
import sys
import io
import wave
import shutil
import threading
import subprocess
import numpy as np
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
    MODE_COLORS = {"INSERT": "#2e7d32", "REMOVE": "#c62828"}

    def __init__(self, root):
        self.root = root
        self.root.title("FreshSense - Layer 1 Barcode Recognition & Inventory")
        self.root.geometry("760x790")
        self.root.configure(bg="#f5f6f8")
        
        # --- Services Setup ---
        self.product_lookup = ProductLookupService()
        self.inventory_manager = InventoryManager()
        self.lookup_cache = {}  # raw barcode -> product dict (avoids repeat catalog/network lookups)
        
        # --- Operation Mode ---
        self.current_mode = "INSERT"
        
        # --- UI Setup ---
        self.header_label = tk.Label(
            root, 
            text="FreshSense Fridge Entry Scanner", 
            font=("Arial", 18, "bold"),
            bg="#f5f6f8",
            fg="#1a1a1a"
        )
        self.header_label.pack(pady=(12, 6))
        
        self.mode_label = tk.Label(
            root,
            text="",
            font=("Arial", 16, "bold"),
            fg="#ffffff",
            padx=18,
            pady=4
        )
        self.mode_label.pack(pady=(0, 6))
        
        self.subtitle_label = tk.Label(
            root, 
            text="Press 'i' for Insert Mode | Press 'r' for Remove Mode", 
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
            text="Show a barcode anywhere in the camera view", 
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
        
        # Audio feedback pre-generation
        self._aplay_available = shutil.which("aplay") is not None
        self._beep_tones = {
            "insert": self._generate_tone_wav(freq=1050, duration=0.12),
            "delete": self._generate_tone_wav(freq=550, duration=0.15),
        }
        
        # --- Keyboard Bindings (i/I = Insert, r/R = Remove) ---
        self.root.bind("<Key>", self.on_key_press)
        self.set_mode("INSERT")
        
        self.update_frame()
        
    def _generate_tone_wav(self, freq=1000, duration=0.12, sample_rate=22050):
        """Pre-generates in-memory WAV bytes for instant, low-latency audio feedback."""
        try:
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            envelope = np.ones_like(t)
            fade_len = min(int(sample_rate * 0.01), len(t) // 2)
            if fade_len > 0:
                envelope[:fade_len] = np.linspace(0, 1, fade_len)
                envelope[-fade_len:] = np.linspace(1, 0, fade_len)

            waveform = (0.35 * envelope * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(waveform.tobytes())
            return buf.getvalue()
        except Exception as e:
            print(f"[Audio] Tone generation error: {e}", flush=True)
            return None

    def play_beep(self, event_type="insert"):
        """Plays an audio beep asynchronously without blocking video playback or Tkinter loop."""
        wav_bytes = self._beep_tones.get(event_type)

        def _worker():
            # 1. Try aplay with pre-generated WAV byte buffer (crisp tone)
            if self._aplay_available and wav_bytes:
                try:
                    proc = subprocess.Popen(['aplay', '-q'], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    proc.communicate(input=wav_bytes, timeout=0.5)
                    return
                except Exception:
                    pass

            # 2. Native Tkinter bell fallback
            try:
                self.root.bell()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def on_key_press(self, event):
        key = (event.char or "").lower()
        if key == "i":
            self.set_mode("INSERT")
        elif key == "r":
            self.set_mode("REMOVE")
            
    def set_mode(self, mode):
        """Switches between INSERT and REMOVE modes and refreshes the mode badge."""
        if mode != self.current_mode:
            # Let an item already in view be processed immediately under the new mode
            self.inventory_manager.reset_cooldowns()
            self.last_barcode_data = None
            print(f"[FreshSense] Switched to {mode} mode", flush=True)
        self.current_mode = mode
        self.mode_label.config(text=f"MODE: [ {mode} ]", bg=self.MODE_COLORS[mode])
        
    def _lookup_product(self, data):
        """Cached product lookup so repeated scans don't re-hit the catalog or network."""
        product = self.lookup_cache.get(data)
        if product is None:
            product = self.product_lookup.lookup(data)
            self.lookup_cache[data] = product
        return product
        
    def _update_removal_display(self, product, barcode_type, removed=True):
        """Updates the Tkinter UI card after a Remove-mode scan."""
        name = product.get("name", "Unknown Product")
        barcode = product.get("barcode")
        units_left = self.inventory_manager.count_item(barcode)
        
        if removed:
            color = "#c62828"  # Red
            title = f"[-] {name}"
            detail = f"✓ Removed from inventory  •  Expiry was: {product.get('expiry_date')}"
        else:
            color = "#e65100"  # Orange
            title = f"[!] {name}"
            detail = "Item not found in inventory"
            
        self.card_title.config(text=title, fg=color)
        self.card_expiry.config(text=detail, fg=color)
        self.card_meta.config(
            text=f"Category: {product.get('category', 'General')}  |  Code: {barcode} ({barcode_type})  |  Units left: {units_left}",
            fg="#555555"
        )
        
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
            
            # 1. Run barcode detection on the full camera FOV, only on throttled frames
            if self.frame_count % self.scan_interval == 0:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                barcodes = decode(gray_frame)
                
                box_color = (0, 200, 0) if self.current_mode == "INSERT" else (0, 0, 220)  # BGR
                
                for barcode in barcodes:
                    data = barcode.data.decode('utf-8')
                    b_type = barcode.type
                    
                    # Barcode coords are already in full-frame space
                    bx, by, bw, bh = barcode.rect
                    
                    # Look up product info and calculate expiry (cached)
                    product = self._lookup_product(data)
                    
                    # Draw mode-coloured bounding box around detected code
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), box_color, 3)
                    
                    # Overlay product name & expiry above barcode box
                    overlay_text = f"{product['name'][:22]} | Exp: {product['expiry_date']}"
                    cv2.putText(
                        frame, 
                        overlay_text, 
                        (bx, max(by - 12, 30)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        box_color, 
                        2
                    )
                    
                    if self.current_mode == "INSERT":
                        # Add item to inventory and print details to console
                        is_new, _ = self.inventory_manager.add_item(product)
                        if is_new:
                            self.play_beep("insert")
                            self.inventory_manager.print_item(product, is_new=True)
                            self._update_ui_display(product, b_type, is_new=True)
                        elif data != self.last_barcode_data:
                            self._update_ui_display(product, b_type, is_new=False)
                    else:
                        # Remove one unit from inventory (None result = still in cooldown)
                        removed, result = self.inventory_manager.remove_item(product)
                        if removed:
                            self.play_beep("delete")
                            self.inventory_manager.print_removal(result, success=True)
                            self._update_removal_display(result, b_type, removed=True)
                        elif result is not None:
                            self.inventory_manager.print_removal(product, success=False)
                            self._update_removal_display(product, b_type, removed=False)
                            
                    self.last_barcode_data = data
            
            # 2. Mode indicator on the video feed
            mode_bgr = (0, 160, 0) if self.current_mode == "INSERT" else (0, 0, 200)
            cv2.putText(frame, f"MODE: {self.current_mode}", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, mode_bgr, 3)
            
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
