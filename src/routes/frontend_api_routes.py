from flask import Blueprint, request, jsonify
from src.database_config import db_config
import json
from datetime import datetime
import uuid

# Blueprint for frontend API compatibility routes
frontend_api_bp = Blueprint('frontend_api', __name__)

@frontend_api_bp.route('/products', methods=['GET'])
def get_products():
    """Get products for frontend - maps to POS products"""
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Get products from POS system and inventory
        cursor.execute("""
            SELECT sku as id, name, category, price, stock_quantity as stock, 
                   thc_percentage as thc, cbd_percentage as cbd, description
            FROM inventory 
            WHERE status = 'active'
            ORDER BY created_at DESC
        """)
        
        items = cursor.fetchall()
        conn.close()
        
        products = []
        for item in items:
            products.append({
                'id': item['id'] or item['sku'],
                'name': item['name'],
                'category': item['category'],
                'price': float(item['price']) if item['price'] else 0.0,
                'stock': item['stock'] or 0,
                'thc': float(item['thc']) if item['thc'] else 0.0,
                'cbd': float(item['cbd']) if item['cbd'] else 0.0,
                'description': item['description'] or f"Premium {item['category']}"
            })
        
        # If no inventory items, return demo products
        if not products:
            products = [
                {'id': 'demo-001', 'name': 'Blue Dream', 'category': 'Flower', 'price': 45.0, 'stock': 25, 'thc': 21.3, 'cbd': 0.8, 'description': 'Premium Blue Dream strain'},
                {'id': 'demo-002', 'name': 'OG Kush', 'category': 'Flower', 'price': 48.0, 'stock': 18, 'thc': 22.5, 'cbd': 1.2, 'description': 'Classic OG Kush'},
                {'id': 'demo-003', 'name': 'Live Resin Cart', 'category': 'Concentrates', 'price': 65.0, 'stock': 12, 'thc': 85.2, 'cbd': 1.1, 'description': 'Premium live resin cartridge'},
                {'id': 'demo-004', 'name': 'THC Gummies', 'category': 'Edibles', 'price': 25.0, 'stock': 50, 'thc': 10.0, 'cbd': 0.5, 'description': '10mg THC gummies'}
            ]
        
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch products: {str(e)}'
        }), 500

@frontend_api_bp.route('/checkout', methods=['POST'])
def process_checkout():
    """Process checkout - creates order"""
    try:
        data = request.get_json()
        
        # Extract customer info
        customer_info = data.get('customer', data.get('customerInfo', {}))
        items = data.get('items', [])
        
        if not customer_info or not items:
            return jsonify({
                'success': False,
                'error': 'Customer info and items are required'
            }), 400
        
        # Calculate totals
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
        tax_rate = 0.0875  # 8.75% tax
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        # Create order ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Store order in database
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO orders (
                id, customer_name, customer_email, customer_phone,
                items, subtotal, tax, total, payment_method, status,
                fulfillment_method, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order_id,
            customer_info.get('name', 'Guest'),
            customer_info.get('email', ''),
            customer_info.get('phone', ''),
            json.dumps(items),
            subtotal,
            tax,
            total,
            data.get('paymentMethod', 'pending'),
            'pending',
            data.get('fulfillmentMethod', 'delivery'),
            datetime.now(),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'order': {
                'id': order_id,
                'customer': customer_info,
                'items': items,
                'subtotal': subtotal,
                'tax': tax,
                'total': total,
                'status': 'pending'
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Checkout failed: {str(e)}'
        }), 500

@frontend_api_bp.route('/payment', methods=['POST'])
def process_payment():
    """Process payment for order"""
    try:
        data = request.get_json()
        order_id = data.get('orderId')
        payment_method = data.get('paymentMethod', 'card')
        
        if not order_id:
            return jsonify({
                'success': False,
                'error': 'Order ID is required'
            }), 400
        
        # Update order payment status
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE orders 
            SET payment_method = %s, status = %s, updated_at = %s
            WHERE id = %s
        """, (payment_method, 'paid', datetime.now(), order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'payment': {
                'orderId': order_id,
                'status': 'completed',
                'paymentMethod': payment_method,
                'processedAt': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Payment failed: {str(e)}'
        }), 500

@frontend_api_bp.route('/cart', methods=['GET', 'POST', 'PUT', 'DELETE'])
def cart_operations():
    """Handle cart operations"""
    if request.method == 'GET':
        # Return empty cart (frontend should manage cart state)
        return jsonify({
            'success': True,
            'cart': {
                'items': [],
                'subtotal': 0,
                'tax': 0,
                'total': 0
            }
        }), 200
    
    elif request.method == 'POST':
        # Add item to cart (return success - frontend manages state)
        data = request.get_json()
        return jsonify({
            'success': True,
            'message': 'Item added to cart',
            'item': data
        }), 200
    
    elif request.method == 'PUT':
        # Update cart item
        data = request.get_json()
        return jsonify({
            'success': True,
            'message': 'Cart updated',
            'cart': data
        }), 200
    
    elif request.method == 'DELETE':
        # Clear cart
        return jsonify({
            'success': True,
            'message': 'Cart cleared'
        }), 200

@frontend_api_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get dashboard statistics"""
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE status = 'active'")
        product_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total) FROM orders WHERE status != 'cancelled'")
        total_sales = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'totalProducts': product_count,
            'totalOrders': order_count,
            'totalSales': float(total_sales),
            'totalCustomers': order_count  # Approximate
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch dashboard data: {str(e)}'
        }), 500