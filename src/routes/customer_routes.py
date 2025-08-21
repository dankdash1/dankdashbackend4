from flask import Blueprint, request, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from src.models.customer import db, Customer, CustomerDocument, AccountingEntry

customer_bp = Blueprint('customers', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
UPLOAD_FOLDER = 'uploads/documents'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@customer_bp.route('/customers', methods=['GET'])
def get_customers():
    """Get all customers with filtering and pagination"""
    try:
        # Get query parameters
        search = request.args.get('search', '')
        status = request.args.get('status')
        customer_type = request.args.get('customer_type')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build query
        query = Customer.query
        
        if search:
            query = query.filter(
                db.or_(
                    Customer.first_name.ilike(f'%{search}%'),
                    Customer.last_name.ilike(f'%{search}%'),
                    Customer.email.ilike(f'%{search}%'),
                    Customer.phone.ilike(f'%{search}%')
                )
            )
        
        if status:
            query = query.filter(Customer.status == status)
        
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type)
        
        # Paginate results
        customers = query.order_by(Customer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'customers': [customer.to_dict() for customer in customers.items],
            'total': customers.total,
            'pages': customers.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    """Get a specific customer by ID"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        return jsonify({
            'success': True,
            'customer': customer.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers', methods=['POST'])
def create_customer():
    """Create a new customer (admin function)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_customer = Customer.query.filter_by(email=data['email']).first()
        if existing_customer:
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create new customer
        customer = Customer(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            status=data.get('status', 'active'),
            customer_type=data.get('customer_type', 'retail'),
            marketing_consent=data.get('marketing_consent', False),
            sms_consent=data.get('sms_consent', False),
            is_verified=data.get('is_verified', True)  # Admin created customers are auto-verified
        )
        
        # Set password if provided
        if data.get('password'):
            customer.set_password(data['password'])
        
        # Add address if provided
        if data.get('address'):
            customer.add_address({
                'type': 'primary',
                'address': data['address'].get('address', ''),
                'city': data['address'].get('city', ''),
                'state': data['address'].get('state', ''),
                'zip_code': data['address'].get('zip_code', ''),
                'country': data['address'].get('country', 'United States')
            })
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer created successfully',
            'customer': customer.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update customer information"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            customer.first_name = data['first_name']
        if 'last_name' in data:
            customer.last_name = data['last_name']
        if 'email' in data:
            # Check if new email already exists
            existing = Customer.query.filter(Customer.email == data['email'], Customer.id != customer_id).first()
            if existing:
                return jsonify({'error': 'Email already exists'}), 400
            customer.email = data['email']
        if 'phone' in data:
            customer.phone = data['phone']
        if 'date_of_birth' in data:
            customer.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        if 'status' in data:
            customer.status = data['status']
        if 'customer_type' in data:
            customer.customer_type = data['customer_type']
        if 'marketing_consent' in data:
            customer.marketing_consent = data['marketing_consent']
        if 'sms_consent' in data:
            customer.sms_consent = data['sms_consent']
        if 'preferred_contact' in data:
            customer.preferred_contact = data['preferred_contact']
        if 'loyalty_points' in data:
            customer.loyalty_points = data['loyalty_points']
        
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer updated successfully',
            'customer': customer.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Delete a customer (soft delete by setting status to inactive)"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        customer.status = 'inactive'
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer deactivated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>/orders', methods=['GET'])
def get_customer_orders(customer_id):
    """Get all orders for a specific customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        orders = customer.orders
        
        return jsonify({
            'success': True,
            'orders': [order.to_dict() for order in orders]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>/documents', methods=['GET'])
def get_customer_documents(customer_id):
    """Get all documents for a specific customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        documents = customer.documents
        
        return jsonify({
            'success': True,
            'documents': [doc.to_dict() for doc in documents]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>/documents', methods=['POST'])
def upload_customer_document():
    """Upload a document for a customer"""
    try:
        customer_id = request.form.get('customer_id')
        document_type = request.form.get('document_type')
        
        if not customer_id or not document_type:
            return jsonify({'error': 'Customer ID and document type are required'}), 400
        
        customer = Customer.query.get_or_404(customer_id)
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{customer_id}_{document_type}_{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Create document record
        document = CustomerDocument(
            customer_id=customer_id,
            document_type=document_type,
            document_name=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.mimetype
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/documents/<int:document_id>/verify', methods=['PUT'])
def verify_document(document_id):
    """Verify a customer document"""
    try:
        document = CustomerDocument.query.get_or_404(document_id)
        data = request.get_json()
        
        document.verification_status = data.get('status', 'approved')
        document.verification_notes = data.get('notes', '')
        document.verification_date = datetime.utcnow()
        document.verified_by = data.get('verified_by')  # Admin user ID
        document.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document verification updated',
            'document': document.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/<int:customer_id>/addresses', methods=['POST'])
def add_customer_address(customer_id):
    """Add a new address for a customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.get_json()
        
        address_data = {
            'type': data.get('type', 'shipping'),
            'address': data.get('address', ''),
            'city': data.get('city', ''),
            'state': data.get('state', ''),
            'zip_code': data.get('zip_code', ''),
            'country': data.get('country', 'United States'),
            'is_default': data.get('is_default', False)
        }
        
        customer.add_address(address_data)
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Address added successfully',
            'customer': customer.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customer_bp.route('/customers/stats', methods=['GET'])
def get_customer_stats():
    """Get customer statistics for dashboard"""
    try:
        total_customers = Customer.query.count()
        active_customers = Customer.query.filter_by(status='active').count()
        new_customers_today = Customer.query.filter(
            Customer.created_at >= datetime.now().date()
        ).count()
        verified_customers = Customer.query.filter_by(is_verified=True).count()
        
        # Top customers by spending
        top_customers = Customer.query.order_by(Customer.total_spent.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_customers': total_customers,
                'active_customers': active_customers,
                'new_customers_today': new_customers_today,
                'verified_customers': verified_customers,
                'verification_rate': (verified_customers / total_customers * 100) if total_customers > 0 else 0
            },
            'top_customers': [customer.to_dict() for customer in top_customers]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_accounting_entry_for_customer(customer_id, transaction_type, amount, description, reference_id=None):
    """Create accounting entry for customer transactions"""
    try:
        entry = AccountingEntry(
            transaction_type=transaction_type,
            reference_type='customer',
            reference_id=reference_id,
            account_code='1200',  # Accounts Receivable
            account_name='Accounts Receivable',
            debit_amount=amount if transaction_type == 'sale' else 0,
            credit_amount=amount if transaction_type == 'refund' else 0,
            description=description,
            customer_id=customer_id,
            transaction_date=datetime.now().date()
        )
        
        db.session.add(entry)
        db.session.commit()
        
    except Exception as e:
        print(f"Error creating accounting entry: {e}")

