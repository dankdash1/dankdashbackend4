from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
import os
import json

enhanced_pos_bp = Blueprint('enhanced_pos', __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'dankdash.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_pos_tables():
    """Initialize POS-specific tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create POS transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pos_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_email TEXT,
            customer_phone TEXT,
            items TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            cash_received REAL,
            change_given REAL,
            status TEXT DEFAULT 'completed',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cashier TEXT,
            notes TEXT
        )
    ''')
    
    # Create inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            thc_content TEXT,
            cbd_content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample products if inventory is empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ('Premium OG Kush', 'Flower', 35.00, 250, '22%', '1%'),
            ('Blue Dream', 'Flower', 32.00, 180, '18%', '2%'),
            ('Mixed Berry Gummies', 'Edibles', 25.00, 500, '10mg', '0%'),
            ('Live Resin Cart', 'Concentrates', 45.00, 75, '85%', '2%'),
            ('CBD Tincture', 'Wellness', 40.00, 120, '0%', '1000mg')
        ]
        
        cursor.executemany('''
            INSERT INTO inventory (product_name, category, price, stock_quantity, thc_content, cbd_content)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
    
    conn.commit()
    conn.close()

# Initialize tables when module loads
init_pos_tables()

@enhanced_pos_bp.route('/products', methods=['GET'])
def get_pos_products():
    """Get all products for POS system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, product_name, category, price, stock_quantity, thc_content, cbd_content
            FROM inventory
            WHERE stock_quantity > 0
            ORDER BY category, product_name
        ''')
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row['id'],
                'name': row['product_name'],
                'category': row['category'],
                'price': float(row['price']),
                'stock': row['stock_quantity'],
                'thc': row['thc_content'],
                'cbd': row['cbd_content']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'products': products
        })
        
    except Exception as e:
        print(f"Error getting POS products: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_pos_bp.route('/sale', methods=['POST'])
def create_pos_sale():
    """Create a new POS sale with full integration"""
    try:
        data = request.get_json()
        
        # Generate unique sale ID
        sale_id = f"SALE-{datetime.now().strftime('%Y%m%d')}-{datetime.now().microsecond}"
        
        # Extract sale data
        items = data.get('items', [])
        customer = data.get('customer', {})
        payment = data.get('payment', {})
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in items)
        tax_rate = 0.0875  # 8.75% tax
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert POS transaction
        cursor.execute('''
            INSERT INTO pos_transactions (
                sale_id, customer_name, customer_email, customer_phone,
                items, subtotal, tax, total, payment_method,
                cash_received, change_given, status, cashier, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sale_id,
            customer.get('name', 'Walk-in Customer'),
            customer.get('email', ''),
            customer.get('phone', ''),
            json.dumps(items),
            subtotal,
            tax,
            total,
            payment.get('method', 'cash'),
            payment.get('cash_received', 0),
            payment.get('change', 0),
            'completed',
            'POS System',
            data.get('notes', '')
        ))
        
        # Update inventory for each item
        for item in items:
            cursor.execute('''
                UPDATE inventory 
                SET stock_quantity = stock_quantity - ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ?
            ''', (item['quantity'], item['name']))
        
        # Create corresponding order in orders table for order management integration
        cursor.execute('''
            INSERT INTO orders (
                id, customer_name, customer_email, customer_phone,
                items, subtotal, tax, total, payment_method,
                status, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"ORD-POS-{datetime.now().strftime('%Y%m%d')}-{datetime.now().microsecond}",
            customer.get('name', 'Walk-in Customer'),
            customer.get('email', ''),
            customer.get('phone', ''),
            json.dumps(items),
            subtotal,
            tax,
            total,
            payment.get('method', 'cash'),
            'completed',
            'pos',
            datetime.now().isoformat()
        ))
        
        # Create accounting entries
        accounting_entries = [
            {
                'account': 'Sales Revenue',
                'type': 'credit',
                'amount': subtotal,
                'description': f'POS Sale {sale_id} - Revenue'
            },
            {
                'account': 'Sales Tax Payable',
                'type': 'credit',
                'amount': tax,
                'description': f'POS Sale {sale_id} - Tax Collected'
            },
            {
                'account': 'Cash' if payment.get('method') == 'cash' else 'Accounts Receivable',
                'type': 'debit',
                'amount': total,
                'description': f'POS Sale {sale_id} - Payment Received'
            }
        ]
        
        # Insert accounting entries
        for entry in accounting_entries:
            cursor.execute('''
                INSERT INTO accounting_entries (
                    transaction_id, account, type, amount, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                sale_id,
                entry['account'],
                entry['type'],
                entry['amount'],
                entry['description'],
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        # Log integration status
        integration_status = {
            'pos_sale_created': True,
            'inventory_updated': True,
            'order_management_integrated': True,
            'accounting_entries_created': True,
            'sale_id': sale_id,
            'total_amount': total,
            'items_sold': len(items),
            'payment_method': payment.get('method', 'cash')
        }
        
        print(f"POS Sale Integration Complete: {integration_status}")
        
        return jsonify({
            'success': True,
            'sale_id': sale_id,
            'total': total,
            'integration_status': integration_status,
            'message': 'Sale completed successfully with full system integration'
        })
        
    except Exception as e:
        print(f"Error creating POS sale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_pos_bp.route('/transactions', methods=['GET'])
def get_pos_transactions():
    """Get all POS transactions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sale_id, customer_name, customer_email, items, 
                   subtotal, tax, total, payment_method, status, timestamp
            FROM pos_transactions
            ORDER BY timestamp DESC
        ''')
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'id': row['sale_id'],
                'customer': {
                    'name': row['customer_name'],
                    'email': row['customer_email']
                },
                'items': json.loads(row['items']) if row['items'] else [],
                'subtotal': float(row['subtotal']),
                'tax': float(row['tax']),
                'total': float(row['total']),
                'paymentMethod': row['payment_method'],
                'status': row['status'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        print(f"Error getting POS transactions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'transactions': []
        }), 500

@enhanced_pos_bp.route('/inventory', methods=['GET'])
def get_inventory():
    """Get current inventory levels"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT product_name, category, price, stock_quantity, thc_content, cbd_content, updated_at
            FROM inventory
            ORDER BY category, product_name
        ''')
        
        inventory = []
        for row in cursor.fetchall():
            inventory.append({
                'name': row['product_name'],
                'category': row['category'],
                'price': float(row['price']),
                'stock': row['stock_quantity'],
                'thc': row['thc_content'],
                'cbd': row['cbd_content'],
                'last_updated': row['updated_at']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'inventory': inventory
        })
        
    except Exception as e:
        print(f"Error getting inventory: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_pos_bp.route('/stats', methods=['GET'])
def get_pos_stats():
    """Get POS statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's sales
        cursor.execute('''
            SELECT COUNT(*) as count, SUM(total) as total
            FROM pos_transactions
            WHERE DATE(timestamp) = DATE('now')
        ''')
        today = cursor.fetchone()
        
        # Get total sales
        cursor.execute('''
            SELECT COUNT(*) as count, SUM(total) as total
            FROM pos_transactions
        ''')
        total = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'today_sales': float(today['total']) if today['total'] else 0,
                'today_transactions': today['count'],
                'total_sales': float(total['total']) if total['total'] else 0,
                'total_transactions': total['count']
            }
        })
        
    except Exception as e:
        print(f"Error getting POS stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

