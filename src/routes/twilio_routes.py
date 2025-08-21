from flask import Blueprint, request, jsonify
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os

twilio_bp = Blueprint('twilio', __name__)

# Twilio configuration (will be set via API)
twilio_config = {
    'account_sid': None,
    'auth_token': None,
    'phone_number': None
}

@twilio_bp.route('/api/twilio/config', methods=['POST'])
def set_twilio_config():
    """Set Twilio configuration"""
    try:
        data = request.get_json()
        twilio_config['account_sid'] = data.get('account_sid')
        twilio_config['auth_token'] = data.get('auth_token')
        twilio_config['phone_number'] = data.get('phone_number')
        
        return jsonify({
            'success': True,
            'message': 'Twilio configuration updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@twilio_bp.route('/api/twilio/test-connection', methods=['POST'])
def test_connection():
    """Test Twilio connection"""
    try:
        if not all([twilio_config['account_sid'], twilio_config['auth_token']]):
            return jsonify({
                'success': False,
                'error': 'Twilio credentials not configured'
            }), 400
        
        client = Client(twilio_config['account_sid'], twilio_config['auth_token'])
        
        # Test by fetching account info
        account = client.api.accounts(twilio_config['account_sid']).fetch()
        
        return jsonify({
            'success': True,
            'message': 'Connection successful',
            'account_status': account.status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@twilio_bp.route('/api/twilio/send-sms', methods=['POST'])
def send_sms():
    """Send SMS message"""
    try:
        print(f"SMS Request received")
        print(f"Twilio config: SID={twilio_config.get('account_sid', 'None')[:10]}..., Token={'Set' if twilio_config.get('auth_token') else 'None'}, Phone={twilio_config.get('phone_number', 'None')}")
        
        if not all([twilio_config['account_sid'], twilio_config['auth_token'], twilio_config['phone_number']]):
            return jsonify({
                'success': False,
                'error': 'Twilio not configured'
            }), 400
        
        data = request.get_json()
        to_number = data.get('to')
        message_body = data.get('message')
        
        print(f"SMS Details: to={to_number}, message='{message_body}'")
        
        if not to_number or not message_body:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: to, message'
            }), 400
        
        client = Client(twilio_config['account_sid'], twilio_config['auth_token'])
        print(f"Twilio client created successfully")
        
        message = client.messages.create(
            body=message_body,
            from_=twilio_config['phone_number'],
            to=to_number
        )
        
        print(f"SMS sent successfully: SID={message.sid}, Status={message.status}")
        
        return jsonify({
            'success': True,
            'message_sid': message.sid,
            'status': message.status
        })
    except Exception as e:
        print(f"SMS Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@twilio_bp.route('/api/twilio/make-call', methods=['POST'])
def make_call():
    """Make voice call"""
    try:
        if not all([twilio_config['account_sid'], twilio_config['auth_token'], twilio_config['phone_number']]):
            return jsonify({
                'success': False,
                'error': 'Twilio not configured'
            }), 400
        
        data = request.get_json()
        to_number = data.get('to')
        call_type = data.get('call_type', 'order_confirmation')
        voice = data.get('voice', 'alice')
        language = data.get('language', 'en-US')
        
        # Custom message data
        customer_name = data.get('customer_name', 'Customer')
        order_id = data.get('order_id', '12345')
        order_total = data.get('order_total', '48.94')
        
        if not to_number:
            return jsonify({
                'success': False,
                'error': 'Missing required field: to'
            }), 400
        
        client = Client(twilio_config['account_sid'], twilio_config['auth_token'])
        
        # Create TwiML URL for the call
        twiml_url = f"{request.url_root}api/twilio/twiml/{call_type}"
        
        call = client.calls.create(
            to=to_number,
            from_=twilio_config['phone_number'],
            url=twiml_url,
            method='POST'
        )
        
        return jsonify({
            'success': True,
            'call_sid': call.sid,
            'status': call.status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@twilio_bp.route('/api/twilio/twiml/<call_type>', methods=['POST'])
def generate_twiml(call_type):
    """Generate TwiML for voice calls"""
    response = VoiceResponse()
    
    # Get call parameters from request
    customer_name = request.form.get('customer_name', 'Customer')
    order_id = request.form.get('order_id', '12345')
    order_total = request.form.get('order_total', '48.94')
    
    if call_type == 'order_confirmation':
        message = f"Hello {customer_name}, this is DankDash calling to confirm your order number {order_id} for ${order_total}. Your delivery is being prepared and will arrive soon. Thank you for choosing DankDash!"
    elif call_type == 'driver_dispatch':
        message = f"Hi driver, you have a new delivery assignment. Customer: {customer_name}, Order total: ${order_total}. Please confirm receipt and proceed to pickup location."
    elif call_type == 'customer_support':
        message = f"Hello {customer_name}, this is DankDash customer support. We received your inquiry and wanted to provide an update. Our team will contact you shortly."
    elif call_type == 'emergency_alert':
        message = f"This is an urgent alert from DankDash. Please check your account for important updates and take immediate action if required."
    else:
        message = "Hello, this is a test call from DankDash. Thank you for using our service."
    
    response.say(message, voice='alice', language='en-US')
    
    return str(response), 200, {'Content-Type': 'text/xml'}

@twilio_bp.route('/api/twilio/test-call', methods=['POST'])
def test_call():
    """Make a test call"""
    try:
        data = request.get_json()
        to_number = data.get('to')
        call_type = data.get('call_type', 'order_confirmation')
        
        if not to_number:
            return jsonify({
                'success': False,
                'error': 'Phone number is required'
            }), 400
        
        # Use the make_call endpoint
        call_data = {
            'to': to_number,
            'call_type': call_type,
            'customer_name': 'Test Customer',
            'order_id': 'TEST123',
            'order_total': '25.99'
        }
        
        return make_call()
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

