import os
import json
import time
from datetime import datetime

class InventoryManager:
    """
    Manages the fridge inventory and logs detected or scanned items.
    
    Features:
    - Debounce/cooldown tracking to avoid duplicate logs while an item remains in view.
    - Persistent JSON storage in data/inventory.json with a clean schema.
    - Formatted console printing for newly identified and removed items.
    """
    
    DEFAULT_INVENTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inventory.json")

    def __init__(self, inventory_path=None, cooldown_seconds=3.0):
        self.inventory_path = inventory_path or self.DEFAULT_INVENTORY_PATH
        self.cooldown_seconds = cooldown_seconds
        self.last_scans = {}  # item_key -> timestamp of most recent sighting
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

    def _next_entry_id(self):
        """Returns the next unique entry_id."""
        return max((item.get("entry_id", 0) for item in self.inventory), default=0) + 1

    @staticmethod
    def _item_key(product_details):
        """Returns a canonical tracking key for cooldowns (barcode if present, else name)."""
        return (
            product_details.get("barcode")
            or product_details.get("name")
            or "UNKNOWN"
        )

    def should_process(self, key):
        """
        Sliding-window presence lock: refreshes `last_scans[key]` on every
        sighting so holding an item in front of the camera never logs it twice.
        The item must be out of view for `cooldown_seconds` before it can
        be processed again.
        """
        now = time.time()
        last_time = self.last_scans.get(key, 0)
        self.last_scans[key] = now
        return (now - last_time) >= self.cooldown_seconds

    def update_item_details(self, product_details):
        """Updates existing inventory entries when async product lookup resolves details."""
        target_name = product_details.get("previous_name")
        if not target_name:
            return
        updated = False
        for item in self.inventory:
            if item.get("name") == target_name:
                item["name"] = product_details.get("name", item["name"])
                item["category"] = product_details.get("category", item["category"])
                item["expiry_date"] = product_details.get("expiry_date", item["expiry_date"])
                item["days_until_expiry"] = product_details.get("days_until_expiry", item["days_until_expiry"])
                item["status"] = product_details.get("status", item["status"])
                updated = True
        if updated:
            self._save_inventory()

    def add_item(self, product_details, bypass_cooldown=False):
        """
        Adds a detected/scanned product to inventory if not within cooldown.
        Returns (success: bool, entry: dict or None)
        """
        key = self._item_key(product_details)
        if not bypass_cooldown and not self.should_process(key):
            return False, None

        entry = {
            "entry_id": self._next_entry_id(),
            "name": product_details.get("name", "Unknown Product"),
            "category": product_details.get("category", "General"),
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_date": product_details.get("expiry_date"),
            "days_until_expiry": product_details.get("days_until_expiry"),
            "status": product_details.get("status", "Fresh"),
        }

        self.inventory.append(entry)
        self._save_inventory()
        return True, entry

    def reset_cooldowns(self):
        """Clears per-item cooldowns (e.g. when switching between Insert/Remove modes)."""
        self.last_scans.clear()

    def remove_item(self, product_details):
        """
        Removes one unit of a product from inventory if not within cooldown.
        The oldest logged entry with a matching name is removed first (FIFO).
        Returns:
          (True, removed_entry)                    -> item removed
          (False, "Item not found in inventory")   -> item not in inventory
          (False, None)                            -> skipped due to cooldown
        """
        key = self._item_key(product_details)
        if not self.should_process(key):
            return False, None

        target_name = product_details.get("name", "").lower()
        for index, item in enumerate(self.inventory):
            if item.get("name", "").lower() == target_name:
                removed_item = self.inventory.pop(index)
                self._save_inventory()
                return True, removed_item

        return False, "Item not found in inventory"

    def count_item(self, name_or_key):
        """Returns how many units of an item are currently in inventory."""
        if not name_or_key:
            return 0
        target = str(name_or_key).lower()
        return sum(
            1 for item in self.inventory
            if item.get("name", "").lower() == target or item.get("barcode") == name_or_key
        )

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
        print(f"  Category     : {product_details.get('category')}")
        print(f"  Expiry Date  : {product_details.get('expiry_date')} ({days_str})")
        print(f"  Freshness    : {product_details.get('status')}")
        print(border + "\n", flush=True)

    def print_removal(self, product_details, success=True):
        """
        Prints a clean, formatted card for an item removed (or not found) during Remove mode.
        """
        header_tag = "ITEM REMOVED FROM INVENTORY" if success else "REMOVAL FAILED - ITEM NOT IN INVENTORY"
        name = product_details.get('name')

        border = "=" * 56
        print("\n" + border)
        print(f"  FRESHSENSE - {header_tag}")
        print(border)
        print(f"  Product Name : {name}")
        print(f"  Category     : {product_details.get('category')}")
        if success:
            print(f"  Expiry Date  : {product_details.get('expiry_date')}")
            print(f"  Logged At    : {product_details.get('scanned_at', 'N/A')}")
        print(f"  Units Left   : {self.count_item(name)}")
        print(border + "\n", flush=True)

    def get_all_items(self):
        """Returns all items in the inventory."""
        return self.inventory
