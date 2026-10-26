import os
import json
import re
import calendar
from datetime import datetime, date, timedelta
import urllib.request
import urllib.error

class ProductLookupService:
    """
    Lightweight barcode lookup and expiry calculation service for FreshSense.
    
    Supports:
    1. GS1 barcode parsing (extracting embedded GTIN and AI (17)/(15) expiry date).
    2. Local product catalog database (data/products.json or internal fallback).
    3. Online fallback to Open Food Facts API (with rapid timeout).
    4. Intelligent shelf life estimation for unregistered items.
    """
    
    DEFAULT_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "products.json")

    def __init__(self, catalog_path=None):
        self.catalog_path = catalog_path or self.DEFAULT_CATALOG_PATH
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        """Loads the local product catalog from JSON file."""
        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ProductLookupService] Warning: Could not read catalog at {self.catalog_path}: {e}")
        return {}

    def save_catalog(self):
        """Persists catalog back to disk."""
        os.makedirs(os.path.dirname(self.catalog_path), exist_ok=True)
        try:
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2)
        except Exception as e:
            print(f"[ProductLookupService] Error saving catalog: {e}")

    def register_product(self, barcode, name, category="General", brand="Unknown", shelf_life_days=7):
        """Allows dynamic registration of a new barcode to the local catalog."""
        barcode_clean = str(barcode).strip()
        self.catalog[barcode_clean] = {
            "name": name,
            "category": category,
            "brand": brand,
            "shelf_life_days": int(shelf_life_days)
        }
        self.save_catalog()

    @staticmethod
    def parse_gs1(barcode_str):
        """
        Parses GS1 barcodes for GTIN and Expiration Date.
        GS1 Application Identifiers (AI):
          (01) GTIN (14 digits)
          (17) Expiration Date (YYMMDD)
          (15) Best Before Date (YYMMDD)
        """
        barcode_str = str(barcode_str).strip()
        gtin = None
        expiry_date = None

        # Check for bracketed AIs e.g. (01)00123456789012(17)261130
        gtin_match = re.search(r'\(01\)(\d{8,14})', barcode_str)
        if gtin_match:
            gtin = gtin_match.group(1)

        expiry_match = re.search(r'\((?:17|15)\)(\d{6})', barcode_str)
        if expiry_match:
            expiry_str = expiry_match.group(1)
            expiry_date = ProductLookupService._parse_yymmdd(expiry_str)

        # If not bracketed, check unbracketed GS1-128 format (starts with 01 and 14-digit GTIN)
        if not gtin and barcode_str.startswith("01") and len(barcode_str) >= 16:
            potential_gtin = barcode_str[2:16]
            if potential_gtin.isdigit():
                gtin = potential_gtin
                remainder = barcode_str[16:]
                if remainder.startswith("17") or remainder.startswith("15"):
                    yymmdd = remainder[2:8]
                    if len(yymmdd) == 6 and yymmdd.isdigit():
                        expiry_date = ProductLookupService._parse_yymmdd(yymmdd)

        return gtin, expiry_date

    @staticmethod
    def _parse_yymmdd(yymmdd):
        """Converts GS1 YYMMDD string to date object, handling day=00 as end-of-month."""
        try:
            yy = int(yymmdd[0:2])
            mm = int(yymmdd[2:4])
            dd = int(yymmdd[4:6])
            
            # GS1 rule: 51-99 is 1951-1999, 00-50 is 2000-2050
            year = 2000 + yy if yy <= 50 else 1900 + yy
            
            # GS1 allows dd=00 meaning the last day of that month
            if dd == 0:
                _, last_day = calendar.monthrange(year, mm)
                dd = last_day
                
            return date(year, mm, dd)
        except Exception:
            return None

    def _fetch_open_food_facts(self, barcode):
        """Queries Open Food Facts for unlisted barcodes with a fast timeout."""
        try:
            url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'FreshSense-FridgeInventory/1.0'}
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("status") == 1 and "product" in data:
                        prod = data["product"]
                        name = prod.get("product_name") or prod.get("generic_name") or "Unknown Product"
                        brand = prod.get("brands") or "Unknown Brand"
                        categories = prod.get("categories", "General Grocery")
                        first_cat = categories.split(",")[0].strip() if categories else "General Grocery"
                        
                        # Check if expiration date is listed in OFF
                        exp_str = prod.get("expiration_date")
                        parsed_exp = None
                        if exp_str:
                            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                                try:
                                    parsed_exp = datetime.strptime(exp_str.strip(), fmt).date()
                                    break
                                except ValueError:
                                    pass

                        return {
                            "name": name,
                            "brand": brand,
                            "category": first_cat,
                            "shelf_life_days": 10,
                            "explicit_expiry": parsed_exp
                        }
        except Exception:
            pass  # Fallback gracefully if offline or request times out
        return None

    def lookup(self, raw_barcode_data):
        """
        Main entry point: Looks up a barcode and returns full item details & expiry.
        
        Returns dict:
        {
            "barcode": str,
            "name": str,
            "category": str,
            "brand": str,
            "expiry_date": str (YYYY-MM-DD),
            "days_until_expiry": int,
            "status": "Fresh" | "Expiring Soon" | "Expired",
            "source": "gs1" | "catalog" | "openfoodfacts" | "fallback"
        }
        """
        barcode_clean = str(raw_barcode_data).strip()
        today = date.today()

        # Step 1: Check for GS1 embedded data (e.g. GS1-128 or DataMatrix)
        gs1_gtin, gs1_expiry = self.parse_gs1(barcode_clean)
        lookup_key = gs1_gtin if gs1_gtin else barcode_clean

        product_info = None
        source = "fallback"

        # Step 2: Check local catalog (try exact match or trimmed GTIN)
        if lookup_key in self.catalog:
            product_info = self.catalog[lookup_key]
            source = "catalog"
        elif barcode_clean in self.catalog:
            product_info = self.catalog[barcode_clean]
            source = "catalog"
        else:
            # Also try matching without leading zeros (e.g., UPC-A vs EAN-13)
            stripped_key = lookup_key.lstrip('0')
            for key, val in self.catalog.items():
                if key.lstrip('0') == stripped_key:
                    product_info = val
                    source = "catalog"
                    break

        # Step 3: Try Open Food Facts if not found locally
        if not product_info and lookup_key.isdigit():
            off_info = self._fetch_open_food_facts(lookup_key)
            if off_info:
                product_info = off_info
                source = "openfoodfacts"

        # Step 4: Fallback for generic/unrecognized packaged goods
        if not product_info:
            product_info = {
                "name": f"Packaged Item ({lookup_key[-6:] if len(lookup_key) > 6 else lookup_key})",
                "brand": "Standard Packaged",
                "category": "Packaged Goods",
                "shelf_life_days": 7
            }
            source = "fallback"

        # Determine Expiry Date:
        # Priority 1: GS1 parsed expiry date
        # Priority 2: Explicit expiry from online / catalog
        # Priority 3: Calculated from shelf_life_days: today + shelf_life_days
        if gs1_expiry:
            final_expiry = gs1_expiry
            source = "gs1"
        elif product_info.get("explicit_expiry"):
            final_expiry = product_info["explicit_expiry"]
        elif product_info.get("shelf_life_days"):
            shelf_days = int(product_info["shelf_life_days"])
            final_expiry = today + timedelta(days=shelf_days)
        else:
            final_expiry = today + timedelta(days=7)

        # Freshness calculation
        days_left = (final_expiry - today).days
        if days_left < 0:
            status = "Expired"
        elif days_left <= 3:
            status = "Expiring Soon"
        else:
            status = "Fresh"

        return {
            "barcode": lookup_key,
            "raw_barcode": barcode_clean,
            "name": product_info.get("name", "Unknown Product"),
            "brand": product_info.get("brand", "Unknown Brand"),
            "category": product_info.get("category", "General"),
            "expiry_date": final_expiry.strftime("%Y-%m-%d"),
            "days_until_expiry": days_left,
            "status": status,
            "source": source
        }

