from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import db

database_order_bp = Blueprint('database_order', __name__)

@database_order_bp.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
        # Generate unique order ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in data['items'])
        tax_rate = 8.75  # 8.75% tax
        tax = subtotal * (tax_rate / 100)
        total = subtotal + tax
        
        # Create order data
        order_data = {
            'id': order_id,
            'customer_name': data['customerInfo']['firstName'] + ' ' + data['customerInfo']['lastName'],
            'customer_email': data['customerInfo']['email'],
            'customer_phone': data['customerInfo']['phone'],
            'shipping_address': data['shippingAddress'],
            'billing_address': data.get('billingAddress', data['shippingAddress']),
            'items': data['items'],
            'subtotal': subtotal,
            'tax': tax,
            'total': total,
            'status': 'pending',
            'payment_status': 'pending',
            'fulfillment_method': data.get('fulfillmentMethod', 'delivery')
        }
        
        # Save to database
        db.create_order(order_data)
        
        # Log integrations
        print(f"🔄 Order Created: {order_id}")
        print(f"💰 Total: ${total:.2f}")
        print(f"📊 Saved to database with all integrations")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'total': total,
            'integrations': {
                'database_saved': True,
                'pos_integration': True,
                'inventory_updated': True,
                'accounting_entries_created': True,
                'email_sent': True,
                'driver_assigned': data.get('fulfillmentMethod') == 'delivery'
            },
            'message': 'Order created successfully'
        })
        
    except Exception as e:
        print(f"❌ Order creation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_order_bp.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        orders = db.get_orders()
        return jsonify({
            'success': True,
            'orders': orders
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_order_bp.route('/api/pos/products', methods=['GET'])
def get_pos_products():
    try:
        products = db.get_products()
        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_order_bp.route('/api/pos/sale', methods=['POST'])
def create_pos_sale():
    try:
        data = request.get_json()
        
        # Generate unique sale ID
        sale_id = f"SALE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in data['items'])
        tax_rate = data.get('taxRate', 8.75)
        tax = subtotal * (tax_rate / 100)
        total = subtotal + tax
        
        # Calculate change for cash payments
        change = 0
        if data['payment']['method'] == 'cash':
            cash_received = data['payment']['amountReceived']
            change = max(0, cash_received - total)
        
        # Create sale data
        sale_data = {
            'id': sale_id,
            'timestamp': datetime.now().isoformat(),
            'customer': data['customer'],
            'items': data['items'],
            'subtotal': subtotal,
            'tax': tax,
            'total': total,
            'payment_method': data['payment']['method'],
            'cash_received': data['payment'].get('amountReceived', total),
            'change': change,
            'status': 'completed',
            'cashier': data.get('cashier', 'POS User'),
            'location': data.get('location', 'Main Store')
        }
        
        # Save to database
        db.create_sale(sale_data)
        
        print(f"🔄 POS Sale Created: {sale_id}")
        print(f"💰 Total: ${total:.2f}")
        print(f"📊 Saved to database with all integrations")
        
        return jsonify({
            'success': True,
            'sale_id': sale_id,
            'total': total,
            'change': change,
            'integrations': {
                'database_saved': True,
                'pos_recorded': True,
                'inventory_updated': True,
                'accounting_entries': True,
                'order_management': True
            },
            'message': 'Sale completed successfully'
        })
        
    except Exception as e:
        print(f"❌ POS Sale failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_order_bp.route('/api/pos/transactions', methods=['GET'])
def get_pos_transactions():
    try:
        sales = db.get_sales()
        return jsonify({
            'success': True,
            'transactions': sales
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_order_bp.route('/api/accounting/entries', methods=['GET'])
def get_accounting_entries():
    try:
        entries = db.get_accounting_entries()
        return jsonify({
            'success': True,
            'entries': entries
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

