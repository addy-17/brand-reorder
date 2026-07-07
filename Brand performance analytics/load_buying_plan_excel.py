"""
Load Toscee buying plan Excel and return structured inventory data.
Reads all brand sheets, parses product data including image URLs.
"""
import pandas as pd
from pathlib import Path


def clean_url(url_str):
    """Clean URL strings that may have extra annotation like 'URL (URL)' format."""
    if not url_str or url_str in ["", "nan", "None"]:
        return ""
    # Remove trailing parenthetical annotation if present
    # e.g. "https://example.com (https://example.com)" -> "https://example.com"
    url_str = url_str.strip()
    if " (" in url_str and url_str.endswith(")"):
        url_str = url_str.split(" (")[0].strip()
    return url_str


def load_buying_plan_excel(filepath):
    """
    Load the Toscee buying plan Excel and return structured inventory.
    
    The Excel has one sheet per brand, with columns:
    Brand Name, Category, Sub Category, Product, Product Title,
    Style Code /Sku, Color, Size, Barcode No, MRP, HSN Code, GST%,
    MATERIAL, Gender, Season, Quantity, UOM, MARGIN %, Net Price,
    Billing Amount, Total Amount, Image URL, Product URL
    
    Returns dict with 'total_inventory' and 'products' list.
    """
    filepath = str(filepath)
    xl = pd.ExcelFile(filepath)
    all_products = []
    
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        # Clean column names - strip whitespace
        df.columns = [str(c).strip() for c in df.columns]
        
        brand_name = sheet_name.strip()
        
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get("Product Title")) and pd.isna(row.get("MRP")):
                continue
            
            product = {
                "brand": str(row.get("Brand Name", brand_name)).strip() if pd.notna(row.get("Brand Name")) else brand_name,
                "category": str(row.get("Category", "")).strip() if pd.notna(row.get("Category")) else "",
                "sub_category": str(row.get("Sub Category", "")).strip() if pd.notna(row.get("Sub Category")) else "",
                "product": str(row.get("Product", "")).strip() if pd.notna(row.get("Product")) else "",
                "product_title": str(row.get("Product Title", "")).strip() if pd.notna(row.get("Product Title")) else "",
                "style_code": str(row.get("Style Code /Sku", "")).strip() if pd.notna(row.get("Style Code /Sku")) else "",
                "color": str(row.get("Color", "")).strip() if pd.notna(row.get("Color")) else "",
                "size": str(row.get("Size", "")).strip() if pd.notna(row.get("Size")) else "",
                "barcode": str(row.get("Barcode No", "")).strip() if pd.notna(row.get("Barcode No")) else "",
                "mrp": float(row["MRP"]) if pd.notna(row.get("MRP")) else None,
                "hsn_code": str(row.get("HSN Code", "")).strip() if pd.notna(row.get("HSN Code")) else "",
                "gst": float(row["GST%"]) if pd.notna(row.get("GST%")) else None,
                "material": str(row.get("MATERIAL", "")).strip() if pd.notna(row.get("MATERIAL")) else "",
                "gender": str(row.get("Gender", "")).strip() if pd.notna(row.get("Gender")) else "",
                "season": str(row.get("Season", "")).strip() if pd.notna(row.get("Season")) else "",
                "uom": str(row.get("UOM", "pcs")).strip() if pd.notna(row.get("UOM")) else "pcs",
                "margin_pct": float(row["MARGIN %"]) if pd.notna(row.get("MARGIN %")) else None,
                "net_price": float(row["Net Price"]) if pd.notna(row.get("Net Price")) else None,
                "billing_amount": float(row["Billing Amount"]) if pd.notna(row.get("Billing Amount")) else None,
                "total_amount": float(row["Total Amount"]) if pd.notna(row.get("Total Amount")) else None,
                "image_url": clean_url(str(row.get("Image URL", ""))) if pd.notna(row.get("Image URL")) else "",
                "product_url": clean_url(str(row.get("Product URL", ""))) if pd.notna(row.get("Product URL")) else "",
            }
            all_products.append(product)
    
    return {
        "total_inventory": len(all_products),
        "products": all_products
    }


def get_brands(inventory_data):
    """Return sorted list of unique brand names."""
    brands = set()
    for item in inventory_data.get("products", []):
        b = (item.get("brand") or "").strip()
        if b:
            brands.add(b)
    return sorted(brands)


def get_categories(inventory_data, brand_name=None):
    """Return sorted list of unique categories (Groups), optionally filtered by brand."""
    cats = set()
    for item in inventory_data.get("products", []):
        if brand_name and (item.get("brand") or "").lower() != brand_name.lower():
            continue
        c = (item.get("category") or "").strip()
        if c:
            cats.add(c)
    return sorted(cats)


def get_sub_categories(inventory_data, brand_name=None, category=None):
    """Return sorted list of unique sub categories, filtered by brand and/or category."""
    subs = set()
    for item in inventory_data.get("products", []):
        if brand_name and (item.get("brand") or "").lower() != brand_name.lower():
            continue
        if category and (item.get("category") or "").lower() != category.lower():
            continue
        s = (item.get("sub_category") or "").strip()
        if s:
            subs.add(s)
    return sorted(subs)