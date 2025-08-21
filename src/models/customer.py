from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    
    # Authentication
    password_hash = db.Column(db.String(255))
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Address Information (stored as JSON for flexibility)
    addresses = db.Column(db.Text)  # JSON array of addresses
    default_address_id = db.Column(db.Integer)
    
    # Customer Status
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    customer_type = db.Column(db.String(20), default='retail')  # retail, wholesale, vip
    
    # Preferences
    marketing_consent = db.Column(db.Boolean, default=False)
    sms_consent = db.Column(db.Boolean, default=False)
    preferred_contact = db.Column(db.String(20), default='email')  # email, sms, phone
    
    # Loyalty and Analytics
    loyalty_points = db.Column(db.Integer, default=0)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Numeric(10, 2), default=0)
    average_order_value = db.Column(db.Numeric(10, 2), default=0)
    last_order_date = db.Column(db.DateTime)
    
    # Account Information
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    orders = db.relationship('Order', backref='customer_record', lazy=True)
    documents = db.relationship('CustomerDocument', backref='customer', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_addresses(self):
        if self.addresses:
            return json.loads(self.addresses)
        return []
    
    def add_address(self, address_data):
        addresses = self.get_addresses()
        address_data['id'] = len(addresses) + 1
        addresses.append(address_data)
        self.addresses = json.dumps(addresses)
    
    def update_order_stats(self, order_total):
        self.total_orders += 1
        self.total_spent += order_total
        self.average_order_value = self.total_spent / self.total_orders
        self.last_order_date = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name} {self.last_name}",
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'is_verified': self.is_verified,
            'addresses': self.get_addresses(),
            'status': self.status,
            'customer_type': self.customer_type,
            'marketing_consent': self.marketing_consent,
            'sms_consent': self.sms_consent,
            'preferred_contact': self.preferred_contact,
            'loyalty_points': self.loyalty_points,
            'total_orders': self.total_orders,
            'total_spent': float(self.total_spent),
            'average_order_value': float(self.average_order_value),
            'last_order_date': self.last_order_date.isoformat() if self.last_order_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class CustomerDocument(db.Model):
    __tablename__ = 'customer_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Document Information
    document_type = db.Column(db.String(50), nullable=False)  # id, license, medical_card, etc.
    document_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    # Verification Status
    verification_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    verified_by = db.Column(db.Integer)  # admin user id
    verification_date = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    
    # Expiration (for IDs, licenses, etc.)
    expiration_date = db.Column(db.Date)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'document_type': self.document_type,
            'document_name': self.document_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'verification_status': self.verification_status,
            'verified_by': self.verified_by,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'verification_notes': self.verification_notes,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'uploaded_at': self.uploaded_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class AccountingEntry(db.Model):
    __tablename__ = 'accounting_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Transaction Information
    transaction_type = db.Column(db.String(20), nullable=False)  # sale, refund, expense, payment
    reference_type = db.Column(db.String(20))  # order, refund, expense
    reference_id = db.Column(db.Integer)  # ID of the referenced record
    
    # Accounting Details
    account_code = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    debit_amount = db.Column(db.Numeric(10, 2), default=0)
    credit_amount = db.Column(db.Numeric(10, 2), default=0)
    
    # Description and Notes
    description = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    
    # Customer/Vendor Information
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    vendor_name = db.Column(db.String(100))
    
    # Date Information
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer)  # admin user id
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_type': self.transaction_type,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'debit_amount': float(self.debit_amount),
            'credit_amount': float(self.credit_amount),
            'description': self.description,
            'notes': self.notes,
            'customer_id': self.customer_id,
            'vendor_name': self.vendor_name,
            'transaction_date': self.transaction_date.isoformat(),
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }

