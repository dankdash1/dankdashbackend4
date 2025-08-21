from flask import Blueprint, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

email_bp = Blueprint('email', __name__)

# Email configuration (will be set via API)
email_config = {
    'provider': 'gmail',  # 'gmail' or 'sendgrid'
    'gmail_user': None,
    'gmail_password': None,
    'sendgrid_api_key': None,
    'from_email': None
}

@email_bp.route('/api/email/config', methods=['POST'])
def set_email_config():
    """Set email configuration"""
    try:
        data = request.get_json()
        email_config['provider'] = data.get('provider', 'gmail')
        email_config['gmail_user'] = data.get('gmail_user')
        email_config['gmail_password'] = data.get('gmail_password')
        email_config['sendgrid_api_key'] = data.get('sendgrid_api_key')
        email_config['from_email'] = data.get('from_email')
        
        return jsonify({
            'success': True,
            'message': 'Email configuration updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_bp.route('/api/email/test-connection', methods=['POST'])
def test_email_connection():
    """Test email connection"""
    try:
        if email_config['provider'] == 'gmail':
            if not email_config['gmail_user'] or not email_config['gmail_password']:
                return jsonify({
                    'success': False,
                    'error': 'Gmail credentials not configured'
                }), 400
            
            # Test Gmail SMTP connection
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email_config['gmail_user'], email_config['gmail_password'])
            server.quit()
            
            return jsonify({
                'success': True,
                'message': 'Gmail connection successful'
            })
        
        elif email_config['provider'] == 'sendgrid':
            if not email_config['sendgrid_api_key']:
                return jsonify({
                    'success': False,
                    'error': 'SendGrid API key not configured'
                }), 400
            
            # Test SendGrid connection (would need sendgrid library)
            return jsonify({
                'success': True,
                'message': 'SendGrid configuration set (install sendgrid library for full testing)'
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid email provider'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_bp.route('/api/email/send', methods=['POST'])
def send_email():
    """Send email"""
    try:
        data = request.get_json()
        to_email = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        email_type = data.get('type', 'notification')
        
        if not all([to_email, subject, body]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: to, subject, body'
            }), 400
        
        if email_config['provider'] == 'gmail':
            return send_gmail(to_email, subject, body)
        elif email_config['provider'] == 'sendgrid':
            return send_sendgrid(to_email, subject, body)
        else:
            return jsonify({
                'success': False,
                'error': 'Email provider not configured'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def send_gmail(to_email, subject, body):
    """Send email via Gmail SMTP"""
    try:
        if not email_config['gmail_user'] or not email_config['gmail_password']:
            return jsonify({
                'success': False,
                'error': 'Gmail not configured'
            }), 400
        
        msg = MIMEMultipart()
        msg['From'] = email_config['from_email'] or email_config['gmail_user']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_config['gmail_user'], email_config['gmail_password'])
        text = msg.as_string()
        server.sendmail(email_config['gmail_user'], to_email, text)
        server.quit()
        
        return jsonify({
            'success': True,
            'message': 'Email sent successfully via Gmail'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Gmail error: {str(e)}'
        }), 500

def send_sendgrid(to_email, subject, body):
    """Send email via SendGrid (placeholder)"""
    # Would need sendgrid library installed
    return jsonify({
        'success': True,
        'message': 'SendGrid integration ready (install sendgrid library)'
    })

@email_bp.route('/api/email/templates/<template_type>', methods=['GET'])
def get_email_template(template_type):
    """Get email template"""
    templates = {
        'order_confirmation': {
            'subject': 'Order Confirmation - DankDash #{order_id}',
            'body': '''
            <html>
            <body>
                <h2>Order Confirmation</h2>
                <p>Hello {customer_name},</p>
                <p>Thank you for your order! Your DankDash order #{order_id} for ${order_total} has been confirmed.</p>
                <p>Delivery details:</p>
                <ul>
                    <li>Order ID: #{order_id}</li>
                    <li>Total: ${order_total}</li>
                    <li>Delivery Address: {delivery_address}</li>
                    <li>Estimated Delivery: {delivery_time}</li>
                </ul>
                <p>You will receive updates as your order is prepared and delivered.</p>
                <p>Thank you for choosing DankDash!</p>
            </body>
            </html>
            '''
        },
        'driver_assignment': {
            'subject': 'New Delivery Assignment - DankDash',
            'body': '''
            <html>
            <body>
                <h2>New Delivery Assignment</h2>
                <p>Hello {driver_name},</p>
                <p>You have a new delivery assignment:</p>
                <ul>
                    <li>Customer: {customer_name}</li>
                    <li>Order ID: #{order_id}</li>
                    <li>Total: ${order_total}</li>
                    <li>Delivery Address: {delivery_address}</li>
                    <li>Customer Phone: {customer_phone}</li>
                </ul>
                <p>Please confirm receipt and proceed to pickup location.</p>
            </body>
            </html>
            '''
        },
        'welcome': {
            'subject': 'Welcome to DankDash!',
            'body': '''
            <html>
            <body>
                <h2>Welcome to DankDash!</h2>
                <p>Hello {customer_name},</p>
                <p>Welcome to DankDash - your premium cannabis delivery service!</p>
                <p>Your account has been successfully created. You can now:</p>
                <ul>
                    <li>Browse our premium cannabis products</li>
                    <li>Place orders for delivery or pickup</li>
                    <li>Track your orders in real-time</li>
                    <li>Manage your account and preferences</li>
                </ul>
                <p>Thank you for choosing DankDash!</p>
            </body>
            </html>
            '''
        }
    }
    
    template = templates.get(template_type)
    if template:
        return jsonify({
            'success': True,
            'template': template
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Template not found'
        }), 404

@email_bp.route('/api/email/test', methods=['POST'])
def test_email():
    """Send test email"""
    try:
        data = request.get_json()
        to_email = data.get('to')
        
        if not to_email:
            return jsonify({
                'success': False,
                'error': 'Email address is required'
            }), 400
        
        subject = "Test Email from DankDash"
        body = '''
        <html>
        <body>
            <h2>Test Email</h2>
            <p>This is a test email from your DankDash notification system.</p>
            <p>If you received this email, your email integration is working correctly!</p>
            <p>Thank you for using DankDash.</p>
        </body>
        </html>
        '''
        
        return send_email_internal(to_email, subject, body)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def send_email_internal(to_email, subject, body):
    """Internal email sending function"""
    if email_config['provider'] == 'gmail':
        return send_gmail(to_email, subject, body)
    elif email_config['provider'] == 'sendgrid':
        return send_sendgrid(to_email, subject, body)
    else:
        return jsonify({
            'success': False,
            'error': 'Email provider not configured'
        }), 400

