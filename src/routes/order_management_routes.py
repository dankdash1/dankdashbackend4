from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
import os
import json

order_management_bp = Blueprint('order_management', __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'dankdash.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@order_management_bp.route('/orders', methods=['GET'])
def get_all_orders():
    """Get all orders from both online checkout and POS"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all orders
        cursor.execute('''
            SELECT id, customer_name, customer_email, customer_phone,
                   items, subtotal, tax, total, payment_method,
                   status, source, created_at
            FROM orders
            ORDER BY created_at DESC
        ''')
        
        orders = []
        for row in cursor.fetchall():
            try:
                items = json.loads(row['items']) if row['items'] else []
            except:
                items = []
                
            orders.append({
                'id': row['id'],
                'customer_name': row['customer_name'],
                'customer_email': row['customer_email'],
                'customer_phone': row['customer_phone'],
                'items': items,
                'subtotal': float(row['subtotal']) if row['subtotal'] else 0,
                'tax': float(row['tax']) if row['tax'] else 0,
                'total': float(row['total']) if row['total'] else 0,
                'payment_method': row['payment_method'],
                'status': row['status'],
                'source': row['source'] or 'website',
                'created_at': row['created_at'],
                'type': 'pos' if row['source'] == 'pos' else 'online'
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total_count': len(orders)
        })
        
    except Exception as e:
        print(f"Error getting orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'orders': []
        }), 500

@order_management_bp.route('/orders/<order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get detailed information for a specific order"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders WHERE id = ?
        ''', (order_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404
        
        try:
            items = json.loads(row['items']) if row['items'] else []
        except:
            items = []
        
        order = {
            'id': row['id'],
            'customer_name': row['customer_name'],
            'customer_email': row['customer_email'],
            'customer_phone': row['customer_phone'],
            'items': items,
            'subtotal': float(row['subtotal']) if row['subtotal'] else 0,
            'tax': float(row['tax']) if row['tax'] else 0,
            'total': float(row['total']) if row['total'] else 0,
            'payment_method': row['payment_method'],
            'status': row['status'],
            'source': row['source'] or 'website',
            'created_at': row['created_at']
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'order': order
        })
        
    except Exception as e:
        print(f"Error getting order details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@order_management_bp.route('/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, order_id))
        
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
            'message': 'Order status updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating order status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@order_management_bp.route('/orders/stats', methods=['GET'])
def get_order_stats():
    """Get order statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total orders
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_orders = cursor.fetchone()['count']
        
        # Get orders by status
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM orders 
            GROUP BY status
        ''')
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Get orders by source
        cursor.execute('''
            SELECT source, COUNT(*) as count 
            FROM orders 
            GROUP BY source
        ''')
        source_counts = {row['source']: row['count'] for row in cursor.fetchall()}
        
        # Get total revenue
        cursor.execute("SELECT SUM(total) as total FROM orders WHERE status != 'cancelled'")
        result = cursor.fetchone()
        total_revenue = float(result['total']) if result['total'] else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'by_status': status_counts,
                'by_source': source_counts
            }
        })
        
    except Exception as e:
        print(f"Error getting order stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

