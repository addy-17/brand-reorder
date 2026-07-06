from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='brand', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), nullable=False, unique=True)
    item_code = db.Column(db.String(100))
    item_name = db.Column(db.String(500))
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'))
    division = db.Column(db.String(100))
    section = db.Column(db.String(100))
    department = db.Column(db.String(100))
    category2 = db.Column(db.String(100))
    color = db.Column(db.String(100))
    size = db.Column(db.String(50))
    material = db.Column(db.String(100))
    gender = db.Column(db.String(50))
    mrp = db.Column(db.Float, default=0)
    vendor_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Upload(db.Model):
    __tablename__ = 'uploads'
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # 'pos' or 'inventory'
    total_rows = db.Column(db.Integer, default=0)
    processed_rows = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='uploaded')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    bill_no = db.Column(db.String(100), nullable=False)
    bill_date = db.Column(db.Date, nullable=False)
    bill_time = db.Column(db.String(50))
    customer_name = db.Column(db.String(255))
    cashier = db.Column(db.String(100))
    payment_mode = db.Column(db.String(50))
    total_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    net_amount = db.Column(db.Float, default=0)
    item_count = db.Column(db.Integer, default=0)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('BillItem', backref='bill', lazy=True)

class BillItem(db.Model):
    __tablename__ = 'bill_items'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    barcode = db.Column(db.String(100))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    item_name = db.Column(db.String(500))
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0)
    basic_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    net_amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReorderHistory(db.Model):
    __tablename__ = 'reorder_history'
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(255), nullable=False)
    barcode = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(500))
    qty_ordered = db.Column(db.Integer, default=0)
    qty_sold_since = db.Column(db.Integer, default=0)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='ordered')  # ordered, received, cancelled
    notes = db.Column(db.Text)

class Prediction(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    prediction_type = db.Column(db.String(50), nullable=False)  # 'revenue', 'product_breakout'
    predicted_value = db.Column(db.Float)  # predicted revenue or rank
    predicted_date = db.Column(db.Date)  # date the prediction was for
    actual_value = db.Column(db.Float)  # actual revenue or rank
    actual_date = db.Column(db.Date)  # date when actual was recorded
    error_percent = db.Column(db.Float)  # error percentage
    accuracy_percent = db.Column(db.Float)  # 100 - error
    confidence = db.Column(db.Float)  # confidence score
    details = db.Column(db.Text)  # JSON string with additional details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
