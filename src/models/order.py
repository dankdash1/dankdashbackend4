from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for guest orders
    
    # Customer Information (for guest orders)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    
    # Order Items (stored as JSON)
    items = db.Column(db.Text, nullable=False)  # JSON string of cart items
    
    # Pricing
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Addresses (stored as JSON)
    shipping_address = db.Column(db.Text, nullable=False)  # JSON string
    billing_address = db.Column(db.Text)  # JSON string
    
    # Shipping and Delivery
    shipping_method = db.Column(db.String(50), nullable=False)
    delivery_type = db.Column(db.String(20))  # 'delivery', 'pickup', 'shipping'
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    payment_id = db.Column(db.String(100))  # External payment processor ID
    
    # Order Status
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, processing, shipped, delivered, cancelled
    fulfillment_status = db.Column(db.String(30), default='pending')
    
    # Delivery/Shipping Tracking
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(50))
    driver_id = db.Column(db.Integer)  # For local delivery
    estimated_delivery = db.Column(db.DateTime)
    
    # Notes
    order_notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    customer = db.relationship('User', backref='orders', foreign_keys=[customer_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'items': json.loads(self.items) if self.items else [],
            'subtotal': float(self.subtotal),
            'shipping_cost': float(self.shipping_cost),
            'tax_amount': float(self.tax_amount),
            'total': float(self.total),
            'shipping_address': json.loads(self.shipping_address) if self.shipping_address else {},
            'billing_address': json.loads(self.billing_address) if self.billing_address else {},
            'shipping_method': self.shipping_method,
            'delivery_type': self.delivery_type,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment_id': self.payment_id,
            'status': self.status,
            'fulfillment_status': self.fulfillment_status,
            'tracking_number': self.tracking_number,
            'carrier': self.carrier,
            'driver_id': self.driver_id,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'order_notes': self.order_notes,
            'internal_notes': self.internal_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DeliveryPartner(db.Model):
    __tablename__ = 'delivery_partners'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(50))  # car, bike, truck
    license_number = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')  # available, busy, offline
    current_location = db.Column(db.String(200))  # lat,lng
    rating = db.Column(db.Numeric(3, 2), default=5.0)
    total_deliveries = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'vehicle_type': self.vehicle_type,
            'license_number': self.license_number,
            'status': self.status,
            'current_location': self.current_location,
            'rating': float(self.rating) if self.rating else 0,
            'total_deliveries': self.total_deliveries,
            'created_at': self.created_at.isoformat()
        }

class OrderDelivery(db.Model):
    __tablename__ = 'order_deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('delivery_partners.id'), nullable=True)
    
    delivery_status = db.Column(db.String(30), default='pending')  # pending, assigned, picked_up, in_transit, delivered, failed
    pickup_time = db.Column(db.DateTime)
    delivery_time = db.Column(db.DateTime)
    delivery_notes = db.Column(db.Text)
    
    # GPS Tracking
    pickup_location = db.Column(db.String(200))  # lat,lng
    delivery_location = db.Column(db.String(200))  # lat,lng
    current_location = db.Column(db.String(200))  # lat,lng
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref='delivery_info')
    partner = db.relationship('DeliveryPartner', backref='deliveries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'partner_id': self.partner_id,
            'delivery_status': self.delivery_status,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'delivery_time': self.delivery_time.isoformat() if self.delivery_time else None,
            'delivery_notes': self.delivery_notes,
            'pickup_location': self.pickup_location,
            'delivery_location': self.delivery_location,
            'current_location': self.current_location,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

