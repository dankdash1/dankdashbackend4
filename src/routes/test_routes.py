from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import traceback

test_bp = Blueprint('test', __name__)

@test_bp.route('/test-order', methods=['POST'])
def test_order():
    """Test endpoint to debug order creation"""
    try:
        data = request.get_json()
        
        # Log the received data
        print("Received order data:", json.dumps(data, indent=2))
        
        # Test basic response
        return jsonify({
            'success': True,
            'message': 'Test endpoint working',
            'received_data': data
        }), 200
        
    except Exception as e:
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'type': type(e).__name__
        }
        print("Test endpoint error:", error_details)
        return jsonify(error_details), 500

@test_bp.route('/test-db', methods=['GET'])
def test_db():
    """Test database connection"""
    try:
        from src.models.order import db, Order
        
        # Try to query the database
        order_count = Order.query.count()
        
        return jsonify({
            'success': True,
            'message': 'Database connection working',
            'order_count': order_count
        }), 200
        
    except Exception as e:
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'type': type(e).__name__
        }
        print("Database test error:", error_details)
        return jsonify(error_details), 500

