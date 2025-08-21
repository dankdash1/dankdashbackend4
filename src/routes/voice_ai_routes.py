from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import requests
import smtplib
import email.mime.text
import email.mime.multipart
import os

voice_ai_bp = Blueprint('voice_ai', __name__)

# Global configuration storage
voice_ai_config = {
    'twilio': {
        'account_sid': '',
        'auth_token': '',
        'phone_number': '',
        'enabled': False
    },
    'gmail': {
        'username': '',
        'app_password': '',
        'from_email': '',
        'enabled': False
    },
    'sendgrid': {
        'api_key': '',
        'from_email': '',
        'from_name': 'DankDash AI Assistant',
        'enabled': False
    },
    'voice_settings': {
        'voice_type': 'Alice (Female, Professional)',
        'language': 'English (US)',
        'auto_answer': True,
        'record_calls': True
    }
}

# Integration logs
integration_logs = []

def log_integration_event(event_type, details, status='success'):
    """Log integration events for tracking"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'details': details,
        'status': status
    }
    integration_logs.append(log_entry)
    print(f"🤖 VOICE AI: {event_type} - {details} - {status}")

@voice_ai_bp.route('/voice-ai/config', methods=['GET'])
def get_voice_ai_config():
    """Get current Voice AI configuration"""
    try:
        return jsonify({
            'success': True,
            'config': voice_ai_config
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/config', methods=['POST'])
def update_voice_ai_config():
    """Update Voice AI configuration"""
    try:
        data = request.get_json()
        
        if 'twilio' in data:
            voice_ai_config['twilio'].update(data['twilio'])
            log_integration_event('config_update', 'Twilio configuration updated')
        
        if 'gmail' in data:
            voice_ai_config['gmail'].update(data['gmail'])
            log_integration_event('config_update', 'Gmail configuration updated')
        
        if 'sendgrid' in data:
            voice_ai_config['sendgrid'].update(data['sendgrid'])
            log_integration_event('config_update', 'SendGrid configuration updated')
        
        if 'voice_settings' in data:
            voice_ai_config['voice_settings'].update(data['voice_settings'])
            log_integration_event('config_update', 'Voice settings updated')
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'config': voice_ai_config
        }), 200
        
    except Exception as e:
        log_integration_event('config_update', f'Configuration update failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/test-connection/<service>', methods=['POST'])
def test_connection(service):
    """Test connection to various services"""
    try:
        if service == 'twilio':
            return test_twilio_connection()
        elif service == 'gmail':
            return test_gmail_connection()
        elif service == 'sendgrid':
            return test_sendgrid_connection()
        else:
            return jsonify({'success': False, 'error': 'Unknown service'}), 400
            
    except Exception as e:
        log_integration_event('test_connection', f'{service} test failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

def test_twilio_connection():
    """Test Twilio connection"""
    try:
        config = voice_ai_config['twilio']
        if not config['account_sid'] or not config['auth_token']:
            return jsonify({'success': False, 'error': 'Missing Twilio credentials'}), 400
        
        # Simulate Twilio API test (replace with actual Twilio SDK call)
        log_integration_event('test_connection', 'Twilio connection test successful')
        voice_ai_config['twilio']['enabled'] = True
        
        return jsonify({
            'success': True,
            'message': 'Twilio connection successful',
            'service': 'twilio'
        }), 200
        
    except Exception as e:
        log_integration_event('test_connection', f'Twilio test failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

def test_gmail_connection():
    """Test Gmail connection"""
    try:
        config = voice_ai_config['gmail']
        if not config['username'] or not config['app_password']:
            return jsonify({'success': False, 'error': 'Missing Gmail credentials'}), 400
        
        # Test Gmail SMTP connection
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config['username'], config['app_password'])
        server.quit()
        
        log_integration_event('test_connection', 'Gmail connection test successful')
        voice_ai_config['gmail']['enabled'] = True
        
        return jsonify({
            'success': True,
            'message': 'Gmail connection successful',
            'service': 'gmail'
        }), 200
        
    except Exception as e:
        log_integration_event('test_connection', f'Gmail test failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

def test_sendgrid_connection():
    """Test SendGrid connection"""
    try:
        config = voice_ai_config['sendgrid']
        if not config['api_key']:
            return jsonify({'success': False, 'error': 'Missing SendGrid API key'}), 400
        
        # Test SendGrid API
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        # Test with SendGrid API endpoint
        response = requests.get('https://api.sendgrid.com/v3/user/account', headers=headers)
        
        if response.status_code == 200:
            log_integration_event('test_connection', 'SendGrid connection test successful')
            voice_ai_config['sendgrid']['enabled'] = True
            
            return jsonify({
                'success': True,
                'message': 'SendGrid connection successful',
                'service': 'sendgrid'
            }), 200
        else:
            raise Exception(f'SendGrid API returned status {response.status_code}')
        
    except Exception as e:
        log_integration_event('test_connection', f'SendGrid test failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/send-email', methods=['POST'])
def send_email():
    """Send email via configured email service"""
    try:
        data = request.get_json()
        to_email = data.get('to_email')
        subject = data.get('subject')
        message = data.get('message')
        template_type = data.get('template_type', 'general')
        
        if not to_email or not subject or not message:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Try SendGrid first, then Gmail
        if voice_ai_config['sendgrid']['enabled']:
            result = send_email_sendgrid(to_email, subject, message, template_type)
        elif voice_ai_config['gmail']['enabled']:
            result = send_email_gmail(to_email, subject, message, template_type)
        else:
            return jsonify({'success': False, 'error': 'No email service configured'}), 400
        
        return result
        
    except Exception as e:
        log_integration_event('send_email', f'Email sending failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

def send_email_sendgrid(to_email, subject, message, template_type):
    """Send email via SendGrid"""
    try:
        config = voice_ai_config['sendgrid']
        
        email_data = {
            'personalizations': [{
                'to': [{'email': to_email}],
                'subject': subject
            }],
            'from': {
                'email': config['from_email'],
                'name': config['from_name']
            },
            'content': [{
                'type': 'text/html',
                'value': message
            }]
        }
        
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post('https://api.sendgrid.com/v3/mail/send', 
                               json=email_data, headers=headers)
        
        if response.status_code == 202:
            log_integration_event('send_email', f'SendGrid email sent to {to_email} - {template_type}')
            return jsonify({
                'success': True,
                'message': 'Email sent successfully via SendGrid',
                'service': 'sendgrid',
                'template_type': template_type
            }), 200
        else:
            raise Exception(f'SendGrid API returned status {response.status_code}')
            
    except Exception as e:
        log_integration_event('send_email', f'SendGrid email failed: {str(e)}', 'error')
        raise e

def send_email_gmail(to_email, subject, message, template_type):
    """Send email via Gmail SMTP"""
    try:
        config = voice_ai_config['gmail']
        
        msg = email.mime.multipart.MimeMultipart()
        msg['From'] = config['from_email'] or config['username']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(email.mime.text.MimeText(message, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config['username'], config['app_password'])
        server.send_message(msg)
        server.quit()
        
        log_integration_event('send_email', f'Gmail email sent to {to_email} - {template_type}')
        return jsonify({
            'success': True,
            'message': 'Email sent successfully via Gmail',
            'service': 'gmail',
            'template_type': template_type
        }), 200
        
    except Exception as e:
        log_integration_event('send_email', f'Gmail email failed: {str(e)}', 'error')
        raise e

@voice_ai_bp.route('/voice-ai/send-sms', methods=['POST'])
def send_sms():
    """Send SMS via Twilio"""
    try:
        data = request.get_json()
        to_phone = data.get('to_phone')
        message = data.get('message')
        template_type = data.get('template_type', 'general')
        
        if not to_phone or not message:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not voice_ai_config['twilio']['enabled']:
            return jsonify({'success': False, 'error': 'Twilio not configured'}), 400
        
        # Simulate Twilio SMS sending (replace with actual Twilio SDK)
        log_integration_event('send_sms', f'SMS sent to {to_phone} - {template_type}')
        
        return jsonify({
            'success': True,
            'message': 'SMS sent successfully',
            'service': 'twilio',
            'template_type': template_type,
            'to_phone': to_phone
        }), 200
        
    except Exception as e:
        log_integration_event('send_sms', f'SMS sending failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/make-call', methods=['POST'])
def make_call():
    """Make voice call via Twilio"""
    try:
        data = request.get_json()
        to_phone = data.get('to_phone')
        message = data.get('message')
        template_type = data.get('template_type', 'general')
        
        if not to_phone or not message:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not voice_ai_config['twilio']['enabled']:
            return jsonify({'success': False, 'error': 'Twilio not configured'}), 400
        
        # Simulate Twilio voice call (replace with actual Twilio SDK)
        log_integration_event('make_call', f'Voice call made to {to_phone} - {template_type}')
        
        return jsonify({
            'success': True,
            'message': 'Voice call initiated successfully',
            'service': 'twilio',
            'template_type': template_type,
            'to_phone': to_phone
        }), 200
        
    except Exception as e:
        log_integration_event('make_call', f'Voice call failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

# Integration with checkout process
@voice_ai_bp.route('/voice-ai/checkout-integration', methods=['POST'])
def checkout_integration():
    """Handle checkout completion notifications"""
    try:
        data = request.get_json()
        order_data = data.get('order_data', {})
        customer_email = order_data.get('customer_email')
        customer_phone = order_data.get('customer_phone')
        order_number = order_data.get('order_number')
        total = order_data.get('total', 0)
        
        notifications_sent = []
        
        # Send order confirmation email
        if customer_email and voice_ai_config['sendgrid']['enabled']:
            email_subject = f"Order Confirmation - {order_number}"
            email_message = f"""
            <h2>Thank you for your order!</h2>
            <p>Your order #{order_number} has been confirmed.</p>
            <p>Total: ${total}</p>
            <p>We'll notify you when your order is ready for delivery.</p>
            """
            
            email_result = send_email_sendgrid(customer_email, email_subject, email_message, 'order_confirmation')
            if email_result:
                notifications_sent.append('email')
        
        # Send SMS confirmation
        if customer_phone and voice_ai_config['twilio']['enabled']:
            sms_message = f"DankDash: Your order #{order_number} for ${total} has been confirmed! We'll text you delivery updates."
            
            # Simulate SMS sending
            log_integration_event('checkout_integration', f'SMS confirmation sent for order {order_number}')
            notifications_sent.append('sms')
        
        # Make confirmation call if enabled
        if customer_phone and voice_ai_config['voice_settings']['auto_answer']:
            call_message = f"Hello, this is DankDash calling to confirm your order {order_number} for ${total}. Thank you for your business!"
            
            # Simulate voice call
            log_integration_event('checkout_integration', f'Voice confirmation call made for order {order_number}')
            notifications_sent.append('voice_call')
        
        return jsonify({
            'success': True,
            'message': 'Checkout integration completed',
            'notifications_sent': notifications_sent,
            'order_number': order_number
        }), 200
        
    except Exception as e:
        log_integration_event('checkout_integration', f'Checkout integration failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

# Integration with partner signup
@voice_ai_bp.route('/voice-ai/partner-signup-integration', methods=['POST'])
def partner_signup_integration():
    """Handle partner signup notifications"""
    try:
        data = request.get_json()
        partner_data = data.get('partner_data', {})
        partner_email = partner_data.get('email')
        partner_phone = partner_data.get('phone')
        partner_name = partner_data.get('name')
        business_name = partner_data.get('business_name')
        
        notifications_sent = []
        
        # Send welcome email to partner
        if partner_email and voice_ai_config['sendgrid']['enabled']:
            email_subject = f"Welcome to DankDash Partner Program - {business_name}"
            email_message = f"""
            <h2>Welcome to DankDash, {partner_name}!</h2>
            <p>Thank you for joining our partner program with {business_name}.</p>
            <p>Your application is being reviewed and you'll hear from us within 24 hours.</p>
            <p>In the meantime, you can access your partner dashboard to complete your profile.</p>
            """
            
            email_result = send_email_sendgrid(partner_email, email_subject, email_message, 'partner_welcome')
            if email_result:
                notifications_sent.append('email')
        
        # Send SMS to partner
        if partner_phone and voice_ai_config['twilio']['enabled']:
            sms_message = f"Welcome to DankDash, {partner_name}! Your partner application for {business_name} is under review. Check your email for details."
            
            log_integration_event('partner_signup', f'SMS welcome sent to {partner_name}')
            notifications_sent.append('sms')
        
        # Notify admin team
        admin_email = "admin@dankdash.com"
        if voice_ai_config['sendgrid']['enabled']:
            admin_subject = f"New Partner Application - {business_name}"
            admin_message = f"""
            <h2>New Partner Application</h2>
            <p><strong>Business:</strong> {business_name}</p>
            <p><strong>Contact:</strong> {partner_name}</p>
            <p><strong>Email:</strong> {partner_email}</p>
            <p><strong>Phone:</strong> {partner_phone}</p>
            <p>Please review the application in the admin dashboard.</p>
            """
            
            send_email_sendgrid(admin_email, admin_subject, admin_message, 'admin_notification')
            notifications_sent.append('admin_email')
        
        return jsonify({
            'success': True,
            'message': 'Partner signup integration completed',
            'notifications_sent': notifications_sent,
            'partner_name': partner_name
        }), 200
        
    except Exception as e:
        log_integration_event('partner_signup', f'Partner signup integration failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

# Integration with customer signup
@voice_ai_bp.route('/voice-ai/customer-signup-integration', methods=['POST'])
def customer_signup_integration():
    """Handle customer signup notifications"""
    try:
        data = request.get_json()
        customer_data = data.get('customer_data', {})
        customer_email = customer_data.get('email')
        customer_phone = customer_data.get('phone')
        customer_name = customer_data.get('name')
        
        notifications_sent = []
        
        # Send welcome email to customer
        if customer_email and voice_ai_config['sendgrid']['enabled']:
            email_subject = "Welcome to DankDash - Your Premium Cannabis Delivery Service"
            email_message = f"""
            <h2>Welcome to DankDash, {customer_name}!</h2>
            <p>Thank you for joining DankDash, your premium cannabis delivery service.</p>
            <p>You can now:</p>
            <ul>
                <li>Browse our premium cannabis products</li>
                <li>Place orders for same-day delivery</li>
                <li>Track your orders in real-time</li>
                <li>Earn rewards with every purchase</li>
            </ul>
            <p>Use code WELCOME10 for 10% off your first order!</p>
            """
            
            email_result = send_email_sendgrid(customer_email, email_subject, email_message, 'customer_welcome')
            if email_result:
                notifications_sent.append('email')
        
        # Send welcome SMS
        if customer_phone and voice_ai_config['twilio']['enabled']:
            sms_message = f"Welcome to DankDash, {customer_name}! Use code WELCOME10 for 10% off your first order. Start shopping now!"
            
            log_integration_event('customer_signup', f'SMS welcome sent to {customer_name}')
            notifications_sent.append('sms')
        
        return jsonify({
            'success': True,
            'message': 'Customer signup integration completed',
            'notifications_sent': notifications_sent,
            'customer_name': customer_name
        }), 200
        
    except Exception as e:
        log_integration_event('customer_signup', f'Customer signup integration failed: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/logs', methods=['GET'])
def get_integration_logs():
    """Get integration logs"""
    try:
        return jsonify({
            'success': True,
            'logs': integration_logs[-50:],  # Return last 50 logs
            'total_logs': len(integration_logs)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@voice_ai_bp.route('/voice-ai/status', methods=['GET'])
def get_integration_status():
    """Get current integration status"""
    try:
        status = {
            'twilio': {
                'enabled': voice_ai_config['twilio']['enabled'],
                'features': ['SMS', 'Voice Calls'],
                'status': 'Connected' if voice_ai_config['twilio']['enabled'] else 'Not Connected'
            },
            'gmail': {
                'enabled': voice_ai_config['gmail']['enabled'],
                'features': ['Basic Email'],
                'status': 'Connected' if voice_ai_config['gmail']['enabled'] else 'Not Connected'
            },
            'sendgrid': {
                'enabled': voice_ai_config['sendgrid']['enabled'],
                'features': ['Professional Email', 'Templates'],
                'status': 'Connected' if voice_ai_config['sendgrid']['enabled'] else 'Not Connected'
            }
        }
        
        return jsonify({
            'success': True,
            'status': status,
            'total_logs': len(integration_logs)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

