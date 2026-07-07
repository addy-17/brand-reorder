"""
Buying Plan Excel Loader
========================
Loads Toscee_buying_plan.xlsx and returns structured product data
with image URLs for integration with BrandIQ.
"""
import os
import sys
import json
from pathlib import Path

# Project root = Path(__file__).parent.parent = "Brand performance analytics"
# Buying plan files are in the project root itself
_PROJECT_ROOT = Path(__file__).parent.parent  # Brand performance analytics
BUYING_PLAN_APP_DIR = _PROJECT_ROOT

if BUYING_PLAN_APP_DIR.exists():
    sys.path.insert(0, str(BUYING_PLAN_APP_DIR))

# Cache for loaded data
_BUYING_PLAN_CACHE = None

# Absolute path to buying plan Excel
DEFAULT_EXCEL_PATH = BUYING_PLAN_APP_DIR / "Toscee_buying_plan.xlsx"
PRODUCT_IMAGES_DIR = BUYING_PLAN_APP_DIR / "product_images"


def load_buying_plan(filepath=None):
    """Load buying plan Excel and return structured inventory with images."""
    global _BUYING_PLAN_CACHE
    
    if filepath is None:
        filepath = DEFAULT_EXCEL_PATH
    
    if _BUYING_PLAN_CACHE is not None:
        return _BUYING_PLAN_CACHE
    
    if not filepath.exists():
        return {"total_inventory": 0, "products": [], "brands": [], "categories": [], 
                "error": f"Buying plan Excel not found: {filepath}\nPlease place Toscee_buying_plan.xlsx in the project root."}
    
    # Check if the Excel loader module exists
    try:
        import importlib.util
        spec = importlib.util.find_spec("load_buying_plan_excel")
        if spec is None:
            return {"total_inventory": 0, "products": [], "brands": [], "categories": [],
                    "error": "Buying plan loader module not found.\nPlease add load_buying_plan_excel.py to the project root."}
    except Exception as e:
        return {"total_inventory": 0, "products": [], "brands": [], "categories": [],
                "error": f"Error checking loader module: {str(e)}"}
    
    try:
        from load_buying_plan_excel import load_buying_plan_excel
        data = load_buying_plan_excel(str(filepath))
        
        # Enrich with local image paths
        products = data.get("products", [])
        for product in products:
            # Check if we have a local image for this product
            brand = (product.get("brand") or "").strip().upper().replace(" ", "_")
            brand_img_dir = PRODUCT_IMAGES_DIR / brand
            
            if brand_img_dir.exists():
                # Look for images matching style_code or barcode
                style_code = (product.get("style_code") or "").strip()
                barcode = (product.get("barcode") or "").strip()
                
                found_image = None
                for img_file in brand_img_dir.iterdir():
                    if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        img_name = img_file.stem.lower()
                        if style_code and style_code.lower() in img_name:
                            found_image = img_file.name
                            break
                        if barcode and barcode.lower() in img_name:
                            found_image = img_file.name
                            break
                
                if found_image:
                    product["local_image"] = f"/api/buying-plan/image/{brand}/{found_image}"
                else:
                    product["local_image"] = ""
            else:
                product["local_image"] = ""
        
        # Get unique brands
        brands = sorted(set(p.get("brand", "").strip() for p in products if p.get("brand", "").strip()))
        categories = sorted(set(p.get("category", "").strip() for p in products if p.get("category", "").strip()))
        
        result = {
            "total_inventory": len(products),
            "products": products,
            "brands": brands,
            "categories": categories
        }
        
        _BUYING_PLAN_CACHE = result
        return result
    
    except Exception as e:
        import traceback
        print(f"Error loading buying plan: {e}")
        print(traceback.format_exc())
        return {"total_inventory": 0, "products": [], "brands": [], "categories": [], "error": str(e)}


def get_buying_plan_products(brand=None, category=None, sub_category=None, search=None):
    """Filter buying plan products."""
    data = load_buying_plan()
    products = data.get("products", [])
    
    if brand:
        products = [p for p in products if (p.get("brand") or "").lower() == brand.lower()]
    if category:
        products = [p for p in products if (p.get("category") or "").lower() == category.lower()]
    if sub_category:
        products = [p for p in products if (p.get("sub_category") or "").lower() == sub_category.lower()]
    if search:
        search_lower = search.lower()
        products = [
            p for p in products
            if search_lower in (p.get("product_title") or "").lower()
            or search_lower in (p.get("style_code") or "").lower()
            or search_lower in (p.get("barcode") or "").lower()
        ]
    
    return products


def get_ai_buying_suggestions(top_brands=None, top_categories=None, limit=20, db=None):
    """
    Get AI-driven suggestions from buying plan based on POS performance.
    
    Logic:
    - Find items in buying plan from brands that perform well in POS
    - Prioritize items from same brand+categories that aren't in POS inventory
    - Score by: brand performance score + category match + newness
    
    db: SQLAlchemy db instance (should be passed from route handler)
    """
    import traceback
    
    data = load_buying_plan()
    products = data.get("products", [])
    
    if not products:
        return {"suggestions": [], "total": 0, "error": "No products in buying plan"}
    
    # Get top selling brands from POS if not provided
    if not top_brands:
        try:
            from models import Brand, Product, BillItem, Bill
            # Get top brands by revenue
            results = db.session.query(
                Brand.name,
                db.func.sum(BillItem.net_amount).label('revenue')
            ).join(Product, Brand.id == Product.brand_id)\
             .join(BillItem, Product.id == BillItem.product_id)\
             .join(Bill)\
             .group_by(Brand.name)\
             .order_by(db.func.sum(BillItem.net_amount).desc())\
             .limit(10).all()
            top_brands = {r.name: r.revenue or 0 for r in results}
            print(f"[BP AI] Top brands from POS: {list(top_brands.keys())}")
        except Exception as e:
            print(f"[BP AI] Error getting top brands: {e}")
            print(traceback.format_exc())
            top_brands = {}
    
    if not top_categories:
        try:
            from models import Product, BillItem, Bill
            results = db.session.query(
                Product.department,
                db.func.sum(BillItem.net_amount).label('revenue')
            ).join(BillItem, Product.id == BillItem.product_id)\
             .join(Bill)\
             .filter(Product.department != '')\
             .group_by(Product.department)\
             .order_by(db.func.sum(BillItem.net_amount).desc())\
             .limit(10).all()
            top_categories = {r.department: r.revenue or 0 for r in results}
        except Exception as e:
            print(f"[BP AI] Error getting top categories: {e}")
            top_categories = {}
    
    # Get existing POS barcodes to avoid suggesting duplicates
    try:
        from models import Product as DBProduct
        existing_barcodes = set(p.barcode for p in DBProduct.query.with_entities(DBProduct.barcode).all() if p.barcode)
    except Exception as e:
        print(f"[BP AI] Error getting existing barcodes: {e}")
        existing_barcodes = set()
    
    # Score each buying plan product
    scored = []
    for product in products:
        barcode = product.get("barcode", "")
        if barcode and barcode in existing_barcodes:
            continue  # Skip items already in POS inventory (only if barcode exists)
        
        brand = product.get("brand", "")
        category = product.get("category", "")
        sub_category = product.get("sub_category", "")
        
        score = 0
        reasons = []
        
        # Brand match score (case-insensitive)
        brand_rev = 0
        brand_lower = brand.lower()
        for b_name, rev in top_brands.items():
            if b_name.lower() == brand_lower:
                brand_rev = rev
                break
        if brand_rev > 0:
            score += 50
            reasons.append(f"🏷️ {brand} is a top seller (₹{brand_rev:,.0f})")
        
        # Category match score
        cat_rev = 0
        for c_name, rev in top_categories.items():
            if c_name.lower() == category.lower() or c_name.lower() == sub_category.lower():
                cat_rev = rev
                break
        if cat_rev > 0:
            score += 30
            reasons.append(f"📦 {category or sub_category} is in demand")
        
        # If no brand or category match, give a small base score so items still show
        if score == 0:
            score = 10
            reasons.append(f"📋 New product from {brand}")
        
        product["suggestion_score"] = score
        product["suggestion_reasons"] = reasons[:2]
        
        # Build image URL
        image_url = product.get("image_url", "") or product.get("local_image", "")
        product["display_image"] = image_url
        
        scored.append(product)
    
    # Sort by score (descending) and return top N
    scored.sort(key=lambda x: x.get("suggestion_score", 0), reverse=True)
    suggestions = scored[:limit]
    
    print(f"[BP AI] Scored {len(scored)} products, returning {len(suggestions)} suggestions")
    
    return {
        "suggestions": suggestions,
        "total": len(scored),
        "displayed": len(suggestions),
        "top_brands": {k: round(v, 2) for k, v in top_brands.items()},
        "top_categories": {k: round(v, 2) for k, v in top_categories.items()}
    }


def clear_cache():
    """Clear the buying plan cache to force reload."""
    global _BUYING_PLAN_CACHE
    _BUYING_PLAN_CACHE = None