from flask import Blueprint, request, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from src.models.order import db, DeliveryPartner
from src.models.customer import CustomerDocument
from src.routes.email_routes import send_email

partner_bp = Blueprint('partners', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
UPLOAD_FOLDER = 'uploads/partner_documents'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class PartnerApplication(db.Model):
    __tablename__ = 'partner_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date)
    
    # Address
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    
    # Vehicle Information
    vehicle_type = db.Column(db.String(50))  # car, bike, truck, van
    vehicle_make = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(50))
    vehicle_year = db.Column(db.Integer)
    license_plate = db.Column(db.String(20))
    
    # License Information
    drivers_license = db.Column(db.String(50))
    license_expiry = db.Column(db.Date)
    
    # Insurance Information
    insurance_company = db.Column(db.String(100))
    insurance_policy = db.Column(db.String(100))
    insurance_expiry = db.Column(db.Date)
    
    # Experience and Availability
    delivery_experience = db.Column(db.Text)
    availability = db.Column(db.Text)  # JSON string of available hours
    preferred_areas = db.Column(db.Text)  # JSON string of preferred delivery areas
    
    # Application Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, under_review
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_date = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer)  # Admin user ID
    review_notes = db.Column(db.Text)
    
    # Background Check
    background_check_status = db.Column(db.String(20), default='pending')
    background_check_date = db.Column(db.DateTime)
    
    # Documents
    documents_uploaded = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name} {self.last_name}",
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'vehicle_type': self.vehicle_type,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_year': self.vehicle_year,
            'license_plate': self.license_plate,
            'drivers_license': self.drivers_license,
            'license_expiry': self.license_expiry.isoformat() if self.license_expiry else None,
            'insurance_company': self.insurance_company,
            'insurance_policy': self.insurance_policy,
            'insurance_expiry': self.insurance_expiry.isoformat() if self.insurance_expiry else None,
            'delivery_experience': self.delivery_experience,
            'availability': self.availability,
            'preferred_areas': self.preferred_areas,
            'status': self.status,
            'application_date': self.application_date.isoformat(),
            'reviewed_date': self.reviewed_date.isoformat() if self.reviewed_date else None,
            'reviewed_by': self.reviewed_by,
            'review_notes': self.review_notes,
            'background_check_status': self.background_check_status,
            'background_check_date': self.background_check_date.isoformat() if self.background_check_date else None,
            'documents_uploaded': self.documents_uploaded
        }

class PartnerDocument(db.Model):
    __tablename__ = 'partner_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('partner_applications.id'), nullable=False)
    
    # Document Information
    document_type = db.Column(db.String(50), nullable=False)  # license, insurance, vehicle_registration, etc.
    document_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    # Verification Status
    verification_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    verified_by = db.Column(db.Integer)  # admin user id
    verification_date = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'document_type': self.document_type,
            'document_name': self.document_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'verification_status': self.verification_status,
            'verified_by': self.verified_by,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'verification_notes': self.verification_notes,
            'uploaded_at': self.uploaded_at.isoformat()
        }

@partner_bp.route('/partner-applications', methods=['POST'])
def submit_partner_application():
    """Submit a new partner application"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'vehicle_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_application = PartnerApplication.query.filter_by(email=data['email']).first()
        if existing_application:
            return jsonify({'error': 'Application with this email already exists'}), 400
        
        # Create new application
        application = PartnerApplication(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            vehicle_type=data['vehicle_type'],
            vehicle_make=data.get('vehicle_make'),
            vehicle_model=data.get('vehicle_model'),
            vehicle_year=data.get('vehicle_year'),
            license_plate=data.get('license_plate'),
            drivers_license=data.get('drivers_license'),
            license_expiry=datetime.strptime(data['license_expiry'], '%Y-%m-%d').date() if data.get('license_expiry') else None,
            insurance_company=data.get('insurance_company'),
            insurance_policy=data.get('insurance_policy'),
            insurance_expiry=datetime.strptime(data['insurance_expiry'], '%Y-%m-%d').date() if data.get('insurance_expiry') else None,
            delivery_experience=data.get('delivery_experience'),
            availability=data.get('availability'),
            preferred_areas=data.get('preferred_areas')
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Send confirmation email
        send_application_confirmation_email(application)
        
        # Notify admin of new application
        send_admin_notification_email(application)
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'application_id': application.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-applications', methods=['GET'])
def get_partner_applications():
    """Get all partner applications with filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build query
        query = PartnerApplication.query
        
        if status:
            query = query.filter(PartnerApplication.status == status)
        
        # Paginate results
        applications = query.order_by(PartnerApplication.application_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'applications': [app.to_dict() for app in applications.items],
            'total': applications.total,
            'pages': applications.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-applications/<int:application_id>', methods=['GET'])
def get_partner_application(application_id):
    """Get a specific partner application"""
    try:
        application = PartnerApplication.query.get_or_404(application_id)
        
        # Get associated documents
        documents = PartnerDocument.query.filter_by(application_id=application_id).all()
        
        result = application.to_dict()
        result['documents'] = [doc.to_dict() for doc in documents]
        
        return jsonify({
            'success': True,
            'application': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-applications/<int:application_id>/review', methods=['PUT'])
def review_partner_application(application_id):
    """Review and approve/reject a partner application"""
    try:
        application = PartnerApplication.query.get_or_404(application_id)
        data = request.get_json()
        
        new_status = data.get('status')
        review_notes = data.get('review_notes', '')
        reviewer_id = data.get('reviewer_id')
        
        if new_status not in ['approved', 'rejected', 'under_review']:
            return jsonify({'error': 'Invalid status'}), 400
        
        old_status = application.status
        application.status = new_status
        application.review_notes = review_notes
        application.reviewed_by = reviewer_id
        application.reviewed_date = datetime.utcnow()
        
        # If approved, create delivery partner record
        if new_status == 'approved':
            partner = DeliveryPartner(
                name=f"{application.first_name} {application.last_name}",
                email=application.email,
                phone=application.phone,
                vehicle_type=application.vehicle_type,
                license_number=application.drivers_license,
                status='available'
            )
            db.session.add(partner)
        
        db.session.commit()
        
        # Send status update email
        send_application_status_email(application, old_status, new_status)
        
        return jsonify({
            'success': True,
            'message': f'Application {new_status} successfully',
            'application': application.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-applications/<int:application_id>/documents', methods=['POST'])
def upload_partner_document():
    """Upload documents for a partner application"""
    try:
        application_id = request.form.get('application_id')
        document_type = request.form.get('document_type')
        
        if not application_id or not document_type:
            return jsonify({'error': 'Application ID and document type are required'}), 400
        
        application = PartnerApplication.query.get_or_404(application_id)
        
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
        filename = f"{application_id}_{document_type}_{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Create document record
        document = PartnerDocument(
            application_id=application_id,
            document_type=document_type,
            document_name=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.mimetype
        )
        
        db.session.add(document)
        
        # Update application documents status
        application.documents_uploaded = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-documents/<int:document_id>/verify', methods=['PUT'])
def verify_partner_document(document_id):
    """Verify a partner document"""
    try:
        document = PartnerDocument.query.get_or_404(document_id)
        data = request.get_json()
        
        document.verification_status = data.get('status', 'approved')
        document.verification_notes = data.get('notes', '')
        document.verification_date = datetime.utcnow()
        document.verified_by = data.get('verified_by')  # Admin user ID
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document verification updated',
            'document': document.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partners', methods=['GET'])
def get_partners():
    """Get all active delivery partners"""
    try:
        partners = DeliveryPartner.query.all()
        return jsonify({
            'success': True,
            'partners': [partner.to_dict() for partner in partners]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partners/<int:partner_id>', methods=['PUT'])
def update_partner(partner_id):
    """Update partner information"""
    try:
        partner = DeliveryPartner.query.get_or_404(partner_id)
        data = request.get_json()
        
        # Update allowed fields
        if 'name' in data:
            partner.name = data['name']
        if 'email' in data:
            partner.email = data['email']
        if 'phone' in data:
            partner.phone = data['phone']
        if 'vehicle_type' in data:
            partner.vehicle_type = data['vehicle_type']
        if 'status' in data:
            partner.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Partner updated successfully',
            'partner': partner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partner_bp.route('/partner-stats', methods=['GET'])
def get_partner_stats():
    """Get partner statistics"""
    try:
        total_applications = PartnerApplication.query.count()
        pending_applications = PartnerApplication.query.filter_by(status='pending').count()
        approved_applications = PartnerApplication.query.filter_by(status='approved').count()
        rejected_applications = PartnerApplication.query.filter_by(status='rejected').count()
        
        active_partners = DeliveryPartner.query.filter_by(status='available').count()
        busy_partners = DeliveryPartner.query.filter_by(status='busy').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_applications': total_applications,
                'pending_applications': pending_applications,
                'approved_applications': approved_applications,
                'rejected_applications': rejected_applications,
                'approval_rate': (approved_applications / total_applications * 100) if total_applications > 0 else 0,
                'active_partners': active_partners,
                'busy_partners': busy_partners,
                'total_partners': active_partners + busy_partners
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_application_confirmation_email(application):
    """Send confirmation email to applicant"""
    subject = "Partner Application Received - DankDash"
    html_content = f"""
    <html>
    <body>
        <h2>Application Received</h2>
        <p>Hi {application.first_name},</p>
        <p>Thank you for applying to become a DankDash delivery partner!</p>
        <p>We have received your application and will review it within 2-3 business days.</p>
        <p><strong>Application ID:</strong> {application.id}</p>
        <p><strong>Next Steps:</strong></p>
        <ul>
            <li>Upload required documents (driver's license, insurance, vehicle registration)</li>
            <li>Complete background check (we'll contact you with instructions)</li>
            <li>Attend orientation session (if approved)</li>
        </ul>
        <p>We'll notify you via email once your application has been reviewed.</p>
        <p>Thank you for your interest in joining the DankDash team!</p>
    </body>
    </html>
    """
    
    send_email(application.email, subject, html_content)

def send_admin_notification_email(application):
    """Send notification to admin about new application"""
    subject = f"New Partner Application - {application.first_name} {application.last_name}"
    html_content = f"""
    <html>
    <body>
        <h2>New Partner Application</h2>
        <p>A new partner application has been submitted:</p>
        <ul>
            <li><strong>Name:</strong> {application.first_name} {application.last_name}</li>
            <li><strong>Email:</strong> {application.email}</li>
            <li><strong>Phone:</strong> {application.phone}</li>
            <li><strong>Vehicle:</strong> {application.vehicle_type}</li>
            <li><strong>Application ID:</strong> {application.id}</li>
            <li><strong>Date:</strong> {application.application_date.strftime('%Y-%m-%d %H:%M')}</li>
        </ul>
        <p>Please review the application in the admin dashboard.</p>
    </body>
    </html>
    """
    
    # Send to admin email (you would configure this)
    admin_email = "admin@dankdash.com"  # Configure this
    send_email(admin_email, subject, html_content)

def send_application_status_email(application, old_status, new_status):
    """Send application status update email"""
    subject = f"Application Status Update - DankDash"
    
    status_messages = {
        'approved': 'Congratulations! Your application has been approved.',
        'rejected': 'Unfortunately, your application has been rejected.',
        'under_review': 'Your application is currently under review.'
    }
    
    html_content = f"""
    <html>
    <body>
        <h2>Application Status Update</h2>
        <p>Hi {application.first_name},</p>
        <p>{status_messages.get(new_status, 'Your application status has been updated.')}</p>
        <p><strong>Application ID:</strong> {application.id}</p>
        <p><strong>Status:</strong> {new_status.replace('_', ' ').title()}</p>
        {f"<p><strong>Notes:</strong> {application.review_notes}</p>" if application.review_notes else ""}
        
        {'<p><strong>Next Steps:</strong></p><ul><li>Complete your profile setup</li><li>Download the DankDash Driver app</li><li>Attend the orientation session</li><li>Start accepting deliveries!</li></ul>' if new_status == 'approved' else ""}
        
        <p>Thank you for your interest in DankDash!</p>
    </body>
    </html>
    """
    
    send_email(application.email, subject, html_content)

