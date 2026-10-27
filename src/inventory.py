import os
import json
import time
from datetime import datetime

class InventoryManager:
    """
    Manages the fridge inventory and logs scanned items.
    
    Features:
    - Debounce/cooldown tracking to avoid duplicate scans while an item remains in view.
    - Persistent JSON storage in data/inventory.json.
    - Formatted console printing for newly identified and removed items.
    """
    
    DEFAULT_INVENTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inventory.json")

    def __init__(self, inventory_path=None, cooldown_seconds=5.0):
        self.inventory_path = inventory_path or self.DEFAULT_INVENTORY_PATH
        self.cooldown_seconds = cooldown_seconds
        self.last_scans = {}  # barcode -> last scan timestamp
        self.inventory = self._load_inventory()

    def _load_inventory(self):
        """Loads existing inventory from disk or starts empty."""
        if os.path.exists(self.inventory_path):
            try:
                with open(self.inventory_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[InventoryManager] Warning: Could not read inventory: {e}")
        return []

    def _save_inventory(self):
        """Saves current inventory list to disk."""
        os.makedirs(os.path.dirname(self.inventory_path), exist_ok=True)
        try:
            with open(self.inventory_path, 'w', encoding='utf-8') as f:
                json.dump(self.inventory, f, indent=2)
        except Exception as e:
            print(f"[InventoryManager] Error saving inventory: {e}")

    def should_process(self, barcode):
        """Checks if enough time has passed since this barcode was last scanned."""
        now = time.time()
        last_time = self.last_scans.get(barcode, 0)
        if (now - last_time) >= self.cooldown_seconds:
            self.last_scans[barcode] = now
            return True
        return False

    def add_item(self, product_details):
        """
        Adds a scanned product to inventory if not within cooldown.
        Returns (success: bool, entry: dict or None)
        """
        barcode = product_details.get("barcode", "UNKNOWN")
        if not self.should_process(barcode):
            return False, None

        entry = {
            "entry_id": len(self.inventory) + 1,
            "barcode": barcode,
            "name": product_details.get("name", "Unknown Product"),
            "category": product_details.get("category", "General"),
            "brand": product_details.get("brand", "Unknown Brand"),
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_date": product_details.get("expiry_date"),
            "days_until_expiry": product_details.get("days_until_expiry"),
            "status": product_details.get("status", "Fresh"),
            "source": product_details.get("source", "catalog")
        }

        self.inventory.append(entry)
        self._save_inventory()
        return True, entry

    def reset_cooldowns(self):
        """Clears per-barcode cooldowns (e.g. when switching between Insert/Remove modes)."""
        self.last_scans.clear()

    def remove_item(self, product_details):
        """
        Removes one unit of a scanned product from inventory if not within cooldown.
        The oldest logged entry with a matching barcode is removed first (FIFO).
        Returns:
          (True, removed_entry)                    -> item removed
          (False, "Item not found in inventory")   -> barcode not in inventory
          (False, None)                            -> skipped due to cooldown
        """
        barcode = product_details.get("barcode", "UNKNOWN")
        if not self.should_process(barcode):
            return False, None

        # Inventory is append-only, so the first match is the oldest logged entry
        for index, item in enumerate(self.inventory):
            if item.get("barcode") == barcode:
                removed_item = self.inventory.pop(index)
                self._save_inventory()
                return True, removed_item

        return False, "Item not found in inventory"

    def count_item(self, barcode):
        """Returns how many units of a barcode are currently in inventory."""
        return sum(1 for item in self.inventory if item.get("barcode") == barcode)

    def print_item(self, product_details, is_new=True):
        """
        Prints a clean, formatted card of the identified product and its expiry.
        """
        header_tag = "NEW ITEM LOGGED TO INVENTORY" if is_new else "ITEM DETECTED"
        days = product_details.get('days_until_expiry', 0)
        days_str = f"{days} days remaining" if days >= 0 else f"EXPIRED by {abs(days)} days"
        
        border = "=" * 56
        print("\n" + border)
        print(f"  FRESHSENSE - {header_tag}")
        print(border)
        print(f"  Product Name : {product_details.get('name')}")
        print(f"  Barcode      : {product_details.get('barcode')} ({product_details.get('raw_barcode', '')})")
        print(f"  Brand        : {product_details.get('brand')}")
        print(f"  Category     : {product_details.get('category')}")
        print(f"  Expiry Date  : {product_details.get('expiry_date')} ({days_str})")
        print(f"  Freshness    : {product_details.get('status')}")
        print(f"  Lookup Source: {product_details.get('source').upper()}")
        print(border + "\n", flush=True)

    def print_removal(self, product_details, success=True):
        """
        Prints a clean, formatted card for an item removed (or not found) during Remove mode.
        """
        header_tag = "ITEM REMOVED FROM INVENTORY" if success else "REMOVAL FAILED - ITEM NOT IN INVENTORY"
        barcode = product_details.get('barcode')
        raw = product_details.get('raw_barcode')
        barcode_str = f"{barcode} ({raw})" if raw and raw != barcode else f"{barcode}"

        border = "=" * 56
        print("\n" + border)
        print(f"  FRESHSENSE - {header_tag}")
        print(border)
        print(f"  Product Name : {product_details.get('name')}")
        print(f"  Barcode      : {barcode_str}")
        print(f"  Brand        : {product_details.get('brand')}")
        print(f"  Category     : {product_details.get('category')}")
        if success:
            print(f"  Expiry Date  : {product_details.get('expiry_date')}")
            print(f"  Logged At    : {product_details.get('scanned_at', 'N/A')}")
        print(f"  Units Left   : {self.count_item(barcode)}")
        print(border + "\n", flush=True)

    def get_all_items(self):
        """Returns all items in the inventory."""
        return self.inventory

