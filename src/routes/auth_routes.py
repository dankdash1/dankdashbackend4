from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt
import secrets
import re
from src.models.customer import db, Customer
from src.routes.email_routes import send_email

auth_bp = Blueprint('auth', __name__)

def generate_jwt_token(customer_id):
    """Generate JWT token for customer authentication"""
    payload = {
        'customer_id': customer_id,
        'exp': datetime.utcnow() + timedelta(days=7),  # Token expires in 7 days
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token and return customer ID"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['customer_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['POST'])
def register():
    """Customer registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password', 'phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if email already exists
        existing_customer = Customer.query.filter_by(email=data['email']).first()
        if existing_customer:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate password
        is_valid, message = validate_password(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Create new customer
        customer = Customer(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            marketing_consent=data.get('marketing_consent', False),
            sms_consent=data.get('sms_consent', False),
            verification_token=secrets.token_urlsafe(32)
        )
        
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
        
        # Send verification email
        verification_link = f"{request.host_url}verify-email?token={customer.verification_token}"
        send_verification_email(customer.email, customer.first_name, verification_link)
        
        # Generate JWT token
        token = generate_jwt_token(customer.id)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful. Please check your email to verify your account.',
            'customer': customer.to_dict(),
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Customer login endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find customer by email
        customer = Customer.query.filter_by(email=data['email']).first()
        if not customer:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        if not customer.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check if account is active
        if customer.status != 'active':
            return jsonify({'error': 'Account is suspended. Please contact support.'}), 401
        
        # Update last login
        customer.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate JWT token
        token = generate_jwt_token(customer.id)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'customer': customer.to_dict(),
            'token': token
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Email verification endpoint"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Verification token is required'}), 400
        
        # Find customer by verification token
        customer = Customer.query.filter_by(verification_token=token).first()
        if not customer:
            return jsonify({'error': 'Invalid or expired verification token'}), 400
        
        # Verify the customer
        customer.is_verified = True
        customer.verification_token = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Forgot password endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Find customer by email
        customer = Customer.query.filter_by(email=email).first()
        if not customer:
            # Don't reveal if email exists or not for security
            return jsonify({
                'success': True,
                'message': 'If the email exists, a password reset link has been sent.'
            })
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        customer.verification_token = reset_token  # Reuse verification_token field
        db.session.commit()
        
        # Send password reset email
        reset_link = f"{request.host_url}reset-password?token={reset_token}"
        send_password_reset_email(customer.email, customer.first_name, reset_link)
        
        return jsonify({
            'success': True,
            'message': 'If the email exists, a password reset link has been sent.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password endpoint"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('password')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        # Validate password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Find customer by reset token
        customer = Customer.query.filter_by(verification_token=token).first()
        if not customer:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Update password
        customer.set_password(new_password)
        customer.verification_token = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get customer profile (requires authentication)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        customer_id = verify_jwt_token(token)
        
        if not customer_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get customer
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        return jsonify({
            'success': True,
            'customer': customer.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update customer profile (requires authentication)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        customer_id = verify_jwt_token(token)
        
        if not customer_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get customer
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            customer.first_name = data['first_name']
        if 'last_name' in data:
            customer.last_name = data['last_name']
        if 'phone' in data:
            customer.phone = data['phone']
        if 'date_of_birth' in data:
            customer.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        if 'marketing_consent' in data:
            customer.marketing_consent = data['marketing_consent']
        if 'sms_consent' in data:
            customer.sms_consent = data['sms_consent']
        if 'preferred_contact' in data:
            customer.preferred_contact = data['preferred_contact']
        
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'customer': customer.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def send_verification_email(email, first_name, verification_link):
    """Send email verification email"""
    subject = "Verify Your DankDash Account"
    html_content = f"""
    <html>
    <body>
        <h2>Welcome to DankDash, {first_name}!</h2>
        <p>Thank you for registering with DankDash. Please click the link below to verify your email address:</p>
        <p><a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
        <p>If you didn't create this account, please ignore this email.</p>
        <p>Best regards,<br>The DankDash Team</p>
    </body>
    </html>
    """
    
    send_email(email, subject, html_content)

def send_password_reset_email(email, first_name, reset_link):
    """Send password reset email"""
    subject = "Reset Your DankDash Password"
    html_content = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>Hi {first_name},</p>
        <p>We received a request to reset your password. Click the link below to create a new password:</p>
        <p><a href="{reset_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
        <p>This link will expire in 24 hours. If you didn't request this reset, please ignore this email.</p>
        <p>Best regards,<br>The DankDash Team</p>
    </body>
    </html>
    """
    
    send_email(email, subject, html_content)

