"""
Data Manager — Central data access layer for FreshSense.
Handles loading, saving, querying, and mutating inventory + products data.
"""
import json
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple


class DataManager:
    """Unified data interface for the FreshSense dashboard."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.inventory_path = os.path.join(project_root, "data", "inventory.json")
        self.products_path = os.path.join(project_root, "data", "products.json")
        self.inventory: List[Dict] = []
        self.products: Dict = {}
        self.reload()

    # ── Loading ───────────────────────────────────────────────────────────

    def reload(self):
        """Re-read both JSON files from disk."""
        self.inventory = self._load_json_list(self.inventory_path)
        self.products = self._load_json_dict(self.products_path)
        # Recalculate dynamic fields
        self._recalculate_statuses()

    def _load_json_list(self, path: str) -> list:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                pass
        return []

    def _load_json_dict(self, path: str) -> dict:
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

    def _save_products(self):
        os.makedirs(os.path.dirname(self.products_path), exist_ok=True)
        with open(self.products_path, "w", encoding="utf-8") as f:
            json.dump(self.products, f, indent=2)

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
        """Get inventory de-duplicated by barcode (keeps latest scan)."""
        seen = {}
        for item in self.inventory:
            bc = item.get("barcode", "")
            if bc not in seen:
                seen[bc] = item
            else:
                # Keep the one with the later scanned_at
                existing_time = seen[bc].get("scanned_at", "")
                new_time = item.get("scanned_at", "")
                if new_time > existing_time:
                    seen[bc] = item
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

    def get_brands(self) -> List[str]:
        """Return sorted unique brands from inventory."""
        brands = set()
        for item in self.inventory:
            brand = item.get("brand", "Unknown")
            if brand:
                brands.add(brand)
        return sorted(brands)

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

    def add_item(
        self,
        name: str,
        category: str = "General",
        brand: str = "Unknown",
        expiry_date: str = "",
        barcode: str = "",
        source: str = "manual",
    ) -> Dict:
        """Add a new item to the inventory manually."""
        today = date.today()

        if not barcode:
            barcode = f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"

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
            "entry_id": len(self.inventory) + 1,
            "barcode": barcode,
            "name": name,
            "category": category,
            "brand": brand,
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_date": expiry_date,
            "days_until_expiry": days_left,
            "status": status,
            "source": source,
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

    def add_to_catalog(self, barcode: str, name: str, category: str, brand: str, shelf_life_days: int):
        self.products[barcode] = {
            "name": name,
            "category": category,
            "brand": brand,
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

        # Earliest expiry
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

