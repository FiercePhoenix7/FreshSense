"""
Data Manager — Central data access layer for FreshSense.
Handles loading, saving, querying, and mutating inventory + products data.
Actively tracks file modification times (mtime & size) for real-time external synchronization.
"""
import json
import os
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple


class DataManager:
    """Unified data interface for the FreshSense dashboard."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.inventory_path = os.path.join(project_root, "data", "inventory.json")
        self.products_path = os.path.join(project_root, "data", "products.json")
        self.shelf_life_path = os.path.join(project_root, "data", "items_shelf_life.json")
        self.last_inventory_mtime: float = 0.0
        self.last_inventory_size: int = 0
        self.last_products_mtime: float = 0.0
        self.inventory: List[Dict] = []
        self.products: Dict = {}
        self.items_shelf_life: Dict = self._load_json_dict(self.shelf_life_path) or {}
        self.reload(force=True)

    # ── Loading & External Sync Tracking ─────────────────────────────────

    def reload(self, force: bool = False) -> bool:
        """
        Re-reads JSON files from disk if modified or if force=True.
        Returns True if new data was detected and loaded.
        """
        inv_mtime = os.path.getmtime(self.inventory_path) if os.path.exists(self.inventory_path) else 0.0
        inv_size = os.path.getsize(self.inventory_path) if os.path.exists(self.inventory_path) else 0
        prod_mtime = os.path.getmtime(self.products_path) if os.path.exists(self.products_path) else 0.0

        changed = False

        if force or inv_mtime != self.last_inventory_mtime or inv_size != self.last_inventory_size:
            new_inv = self._load_json_list(self.inventory_path)
            if new_inv is not None:
                self.inventory = new_inv
                self.last_inventory_mtime = inv_mtime
                self.last_inventory_size = inv_size
                self._recalculate_statuses()
                changed = True

        if force or prod_mtime != self.last_products_mtime:
            new_prod = self._load_json_dict(self.products_path)
            if new_prod is not None:
                self.products = new_prod
                self.last_products_mtime = prod_mtime
                changed = True

        return changed

    def has_inventory_changed(self) -> bool:
        """
        Checks if inventory.json on disk has been modified externally since last reload.
        Checks both mtime and file size to ensure zero missed updates.
        """
        if not os.path.exists(self.inventory_path):
            return False
        try:
            current_mtime = os.path.getmtime(self.inventory_path)
            current_size = os.path.getsize(self.inventory_path)
            return (current_mtime != self.last_inventory_mtime or current_size != self.last_inventory_size)
        except OSError:
            return False

    def _load_json_list(self, path: str) -> Optional[list]:
        if os.path.exists(path):
            # Retry once if another external process is currently writing
            for attempt in range(2):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data if isinstance(data, list) else []
                except (json.JSONDecodeError, OSError):
                    if attempt == 0:
                        time.sleep(0.05)
            # If still locked/writing, preserve existing memory rather than clearing
            return self.inventory if self.inventory else []
        return []

    def _load_json_dict(self, path: str) -> Optional[dict]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                pass
        return {}

    # ── Saving ────────────────────────────────────────────────────────────

    def _save_inventory(self):
        os.makedirs(os.path.dirname(self.inventory_path), exist_ok=True)
        with open(self.inventory_path, "w", encoding="utf-8") as f:
            json.dump(self.inventory, f, indent=2)
        if os.path.exists(self.inventory_path):
            self.last_inventory_mtime = os.path.getmtime(self.inventory_path)
            self.last_inventory_size = os.path.getsize(self.inventory_path)

    def _save_products(self):
        os.makedirs(os.path.dirname(self.products_path), exist_ok=True)
        with open(self.products_path, "w", encoding="utf-8") as f:
            json.dump(self.products, f, indent=2)
        if os.path.exists(self.products_path):
            self.last_products_mtime = os.path.getmtime(self.products_path)

    # ── Status Recalculation ──────────────────────────────────────────────

    def _recalculate_statuses(self):
        """Update days_until_expiry and status for every inventory item based on today."""
        today = date.today()
        for item in self.inventory:
            exp_str = item.get("expiry_date")
            if exp_str:
                try:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                    days_left = (exp_date - today).days
                    item["days_until_expiry"] = days_left
                    if days_left < 0:
                        item["status"] = "Expired"
                    elif days_left <= 3:
                        item["status"] = "Expiring Soon"
                    else:
                        item["status"] = "Fresh"
                except ValueError:
                    item["days_until_expiry"] = None
                    item["status"] = "Unknown"

    # ── Queries ───────────────────────────────────────────────────────────

    def get_all_items(self) -> List[Dict]:
        return self.inventory

    def get_item_count(self) -> int:
        return len(self.inventory)

    def get_unique_items(self) -> List[Dict]:
        """Get inventory de-duplicated by product name (keeps latest scan)."""
        seen = {}
        for item in self.inventory:
            key = item.get("name", "").strip().lower()
            if key not in seen:
                seen[key] = item
            else:
                existing_time = seen[key].get("scanned_at", "")
                new_time = item.get("scanned_at", "")
                if new_time > existing_time:
                    seen[key] = item
        return list(seen.values())

    def get_expiring_items(self, days_threshold: int = 3) -> List[Dict]:
        """Items expiring within `days_threshold` days (not yet expired)."""
        return [
            item for item in self.inventory
            if item.get("days_until_expiry") is not None
            and 0 <= item["days_until_expiry"] <= days_threshold
        ]

    def get_expired_items(self) -> List[Dict]:
        """Items that have already expired."""
        return [
            item for item in self.inventory
            if item.get("days_until_expiry") is not None
            and item["days_until_expiry"] < 0
        ]

    def get_fresh_items(self) -> List[Dict]:
        """Items with > 3 days until expiry."""
        return [
            item for item in self.inventory
            if item.get("days_until_expiry") is not None
            and item["days_until_expiry"] > 3
        ]

    def get_categories(self) -> List[str]:
        """Return sorted unique categories from inventory."""
        cats = set()
        for item in self.inventory:
            cat = item.get("category", "General")
            if cat:
                cats.add(cat)
        return sorted(cats)

    def get_items_by_status(self, status: str) -> List[Dict]:
        return [item for item in self.inventory if item.get("status") == status]

    def get_category_distribution(self) -> Dict[str, int]:
        """Count of items per category."""
        dist = {}
        for item in self.inventory:
            cat = item.get("category", "General")
            dist[cat] = dist.get(cat, 0) + 1
        return dist

    def get_status_distribution(self) -> Dict[str, int]:
        """Count of items per freshness status."""
        dist = {"Fresh": 0, "Expiring Soon": 0, "Expired": 0}
        for item in self.inventory:
            status = item.get("status", "Unknown")
            dist[status] = dist.get(status, 0) + 1
        return dist

    def get_expiry_timeline(self) -> List[Tuple[str, int]]:
        """Returns list of (date_str, count) for items grouped by expiry date."""
        timeline = {}
        for item in self.inventory:
            exp = item.get("expiry_date")
            if exp:
                timeline[exp] = timeline.get(exp, 0) + 1
        return sorted(timeline.items(), key=lambda x: x[0])

    # ── Mutations ─────────────────────────────────────────────────────────

    def _next_entry_id(self) -> int:
        return max((item.get("entry_id", 0) for item in self.inventory), default=0) + 1

    def add_item(
        self,
        name: str,
        category: str = "General",
        expiry_date: str = "",
    ) -> Dict:
        """Add a new item to the inventory manually."""
        today = date.today()

        days_left = None
        status = "Fresh"
        if expiry_date:
            try:
                exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                days_left = (exp - today).days
                if days_left < 0:
                    status = "Expired"
                elif days_left <= 3:
                    status = "Expiring Soon"
            except ValueError:
                pass

        entry = {
            "entry_id": self._next_entry_id(),
            "name": name,
            "category": category,
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_date": expiry_date,
            "days_until_expiry": days_left,
            "status": status,
        }

        self.inventory.append(entry)
        self._save_inventory()
        return entry

    def remove_item(self, entry_id: int) -> bool:
        """Remove an item by its entry_id."""
        before = len(self.inventory)
        self.inventory = [i for i in self.inventory if i.get("entry_id") != entry_id]
        if len(self.inventory) < before:
            self._save_inventory()
            return True
        return False

    def update_item(self, entry_id: int, updates: Dict) -> bool:
        """Update fields on an item by entry_id."""
        for item in self.inventory:
            if item.get("entry_id") == entry_id:
                item.update(updates)
                self._recalculate_statuses()
                self._save_inventory()
                return True
        return False

    # ── Product Catalog Helpers ───────────────────────────────────────────

    def get_product_catalog(self) -> Dict:
        return self.products

    def add_to_catalog(self, barcode: str, name: str, category: str, shelf_life_days: int):
        self.products[barcode] = {
            "name": name,
            "category": category,
            "shelf_life_days": shelf_life_days,
        }
        self._save_products()

    # ── Summary Stats ─────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """Dashboard summary statistics."""
        total = len(self.inventory)
        unique = len(self.get_unique_items())
        expiring = len(self.get_expiring_items())
        expired = len(self.get_expired_items())
        fresh = len(self.get_fresh_items())
        categories = len(self.get_categories())

        earliest = None
        for item in self.inventory:
            exp = item.get("expiry_date")
            if exp:
                if earliest is None or exp < earliest:
                    earliest = exp

        return {
            "total_items": total,
            "unique_items": unique,
            "fresh": fresh,
            "expiring_soon": expiring,
            "expired": expired,
            "categories": categories,
            "earliest_expiry": earliest,
        }
