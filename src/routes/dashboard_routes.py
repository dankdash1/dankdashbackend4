from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import os

dashboard_bp = Blueprint('dashboard', __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'dankdash.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total orders
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_orders = cursor.fetchone()['count']
        
        # Get total sales amount
        cursor.execute("SELECT SUM(total) as total FROM orders WHERE status != 'cancelled'")
        result = cursor.fetchone()
        total_sales = result['total'] if result['total'] else 0
        
        # Get total customers (mock data for now)
        total_customers = 150
        
        # Get total products (mock data for now)
        total_products = 25
        
        conn.close()
        
        return jsonify({
            'success': True,
            'totalOrders': total_orders,
            'totalSales': float(total_sales),
            'totalCustomers': total_customers,
            'totalProducts': total_products
        })
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': True,
            'totalOrders': 0,
            'totalSales': 0,
            'totalCustomers': 0,
            'totalProducts': 0
        })

@dashboard_bp.route('/ecommerce/stats', methods=['GET'])
def get_ecommerce_stats():
    """Get eCommerce specific statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get online orders (orders from website)
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE source = 'website'")
        result = cursor.fetchone()
        online_orders = result['count'] if result else 0
        
        # Get revenue from online orders
        cursor.execute("SELECT SUM(total) as total FROM orders WHERE source = 'website' AND status != 'cancelled'")
        result = cursor.fetchone()
        revenue = result['total'] if result and result['total'] else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'onlineOrders': online_orders,
            'revenue': float(revenue),
            'conversionRate': 3.2,  # Mock data
            'abandonedCarts': 23,   # Mock data
            'visitors': 1247,       # Mock data
            'pageViews': 3891       # Mock data
        })
        
    except Exception as e:
        print(f"Error getting ecommerce stats: {e}")
        return jsonify({
            'success': True,
            'onlineOrders': 0,
            'revenue': 0,
            'conversionRate': 0,
            'abandonedCarts': 0,
            'visitors': 0,
            'pageViews': 0
        })

@dashboard_bp.route('/recent-activity', methods=['GET'])
def get_recent_activity():
    """Get recent system activity"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent orders
        cursor.execute("""
            SELECT id, customer_name, total, status, created_at, source
            FROM orders 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row['id'],
                'customer_name': row['customer_name'],
                'total': float(row['total']),
                'status': row['status'],
                'created_at': row['created_at'],
                'source': row['source'] or 'website'
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'recent_orders': orders
        })
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return jsonify({
            'success': True,
            'recent_orders': []
        })

