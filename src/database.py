import sqlite3
import json
from datetime import datetime
import os

class Database:
    def __init__(self, db_path="dankdash.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Sales table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                items TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT NOT NULL,
                cash_received REAL,
                change_amount REAL,
                status TEXT DEFAULT 'completed',
                cashier TEXT,
                location TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                date_of_birth TEXT,
                address TEXT,
                id_number TEXT,
                id_verified BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table (for online orders)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT,
                customer_phone TEXT,
                shipping_address TEXT,
                billing_address TEXT,
                items TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_status TEXT DEFAULT 'pending',
                fulfillment_method TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                thc_content REAL DEFAULT 0,
                cbd_content REAL DEFAULT 0,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Accounting entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounting_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize with sample products if empty
        self.init_sample_data()
    
    def init_sample_data(self):
        """Initialize with sample products if inventory is empty"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM inventory")
        count = cursor.fetchone()[0]
        
        if count == 0:
            sample_products = [
                ('SKU-001', 'Premium OG Kush', 'Flower', 35.00, 250, 22.5, 1.2, 'Premium indoor grown OG Kush'),
                ('SKU-002', 'Blue Dream', 'Flower', 32.00, 90, 21.3, 2.1, 'Classic Blue Dream strain'),
                ('SKU-003', 'Mixed Berry Gummies', 'Edibles', 25.00, 880, 10.0, 0.5, '10mg THC gummies'),
                ('SKU-004', 'OG Kush Shatter', 'Concentrates', 65.00, 48, 87.3, 1.1, 'High potency shatter'),
                ('SKU-005', 'Glass Spoon Pipe', 'Accessories', 15.00, 180, 0.0, 0.0, 'Hand-blown glass pipe')
            ]
            
            cursor.executemany('''
                INSERT INTO inventory (id, name, category, price, stock, thc_content, cbd_content, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_products)
            
            conn.commit()
        
        conn.close()
    
    def create_sale(self, sale_data):
        """Create a new sale record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sales (
                id, timestamp, customer_name, customer_email, customer_phone,
                items, subtotal, tax, total, payment_method, cash_received,
                change_amount, status, cashier, location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sale_data['id'],
            sale_data['timestamp'],
            sale_data['customer']['name'],
            sale_data['customer'].get('email', ''),
            sale_data['customer'].get('phone', ''),
            json.dumps(sale_data['items']),
            sale_data['subtotal'],
            sale_data['tax'],
            sale_data['total'],
            sale_data['payment_method'],
            sale_data.get('cash_received', 0),
            sale_data.get('change', 0),
            sale_data.get('status', 'completed'),
            sale_data.get('cashier', 'POS User'),
            sale_data.get('location', 'Main Store')
        ))
        
        conn.commit()
        conn.close()
        
        # Update inventory
        self.update_inventory_from_sale(sale_data['items'])
        
        # Create accounting entries
        self.create_accounting_entries(sale_data)
        
        return sale_data['id']
    
    def get_sales(self, limit=100):
        """Get all sales records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sales 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        sales = []
        for row in rows:
            sale = {
                'id': row[0],
                'timestamp': row[1],
                'customer': {
                    'name': row[2],
                    'email': row[3],
                    'phone': row[4]
                },
                'items': json.loads(row[5]),
                'subtotal': row[6],
                'tax': row[7],
                'total': row[8],
                'paymentMethod': row[9],
                'cashReceived': row[10],
                'change': row[11],
                'status': row[12],
                'cashier': row[13],
                'location': row[14]
            }
            sales.append(sale)
        
        return sales
    
    def create_order(self, order_data):
        """Create a new order record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (
                id, customer_name, customer_email, customer_phone,
                shipping_address, billing_address, items, subtotal, tax, total,
                status, payment_status, fulfillment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data['id'],
            order_data['customer_name'],
            order_data.get('customer_email', ''),
            order_data.get('customer_phone', ''),
            json.dumps(order_data.get('shipping_address', {})),
            json.dumps(order_data.get('billing_address', {})),
            json.dumps(order_data['items']),
            order_data['subtotal'],
            order_data['tax'],
            order_data['total'],
            order_data.get('status', 'pending'),
            order_data.get('payment_status', 'pending'),
            order_data.get('fulfillment_method', 'delivery')
        ))
        
        conn.commit()
        conn.close()
        
        return order_data['id']
    
    def get_orders(self, limit=100):
        """Get all orders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in rows:
            order = {
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'customer_phone': row[3],
                'shipping_address': json.loads(row[4]) if row[4] else {},
                'billing_address': json.loads(row[5]) if row[5] else {},
                'items': json.loads(row[6]),
                'subtotal': row[7],
                'tax': row[8],
                'total': row[9],
                'status': row[10],
                'payment_status': row[11],
                'fulfillment_method': row[12],
                'created_at': row[13],
                'updated_at': row[14]
            }
            orders.append(order)
        
        return orders
    
    def get_products(self):
        """Get all products from inventory"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM inventory ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        
        products = []
        for row in rows:
            product = {
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'price': row[3],
                'stock': row[4],
                'thc': row[5],
                'cbd': row[6],
                'description': row[7]
            }
            products.append(product)
        
        return products
    
    def update_inventory_from_sale(self, items):
        """Update inventory after a sale"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for item in items:
            cursor.execute('''
                UPDATE inventory 
                SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (item['quantity'], item['id']))
        
        conn.commit()
        conn.close()
    
    def create_accounting_entries(self, sale_data):
        """Create accounting entries for a sale"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        transaction_id = sale_data['id']
        total = sale_data['total']
        tax = sale_data['tax']
        subtotal = sale_data['subtotal']
        
        # Revenue entry (Credit)
        cursor.execute('''
            INSERT INTO accounting_entries (transaction_id, account_name, account_type, credit_amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_id, 'Sales Revenue', 'Revenue', subtotal, f'Sale revenue for {transaction_id}'))
        
        # Tax entry (Credit)
        if tax > 0:
            cursor.execute('''
                INSERT INTO accounting_entries (transaction_id, account_name, account_type, credit_amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (transaction_id, 'Sales Tax Payable', 'Liability', tax, f'Sales tax for {transaction_id}'))
        
        # Cash/Card entry (Debit)
        account_name = 'Cash' if sale_data['payment_method'] == 'cash' else 'Accounts Receivable'
        cursor.execute('''
            INSERT INTO accounting_entries (transaction_id, account_name, account_type, debit_amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_id, account_name, 'Asset', total, f'Payment received for {transaction_id}'))
        
        # Cost of Goods Sold (simplified)
        cogs = subtotal * 0.4  # Assume 40% cost ratio
        cursor.execute('''
            INSERT INTO accounting_entries (transaction_id, account_name, account_type, debit_amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_id, 'Cost of Goods Sold', 'Expense', cogs, f'COGS for {transaction_id}'))
        
        # Inventory reduction (Credit)
        cursor.execute('''
            INSERT INTO accounting_entries (transaction_id, account_name, account_type, credit_amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_id, 'Inventory', 'Asset', cogs, f'Inventory reduction for {transaction_id}'))
        
        conn.commit()
        conn.close()
    
    def get_accounting_entries(self, transaction_id=None):
        """Get accounting entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if transaction_id:
            cursor.execute('SELECT * FROM accounting_entries WHERE transaction_id = ? ORDER BY created_at', (transaction_id,))
        else:
            cursor.execute('SELECT * FROM accounting_entries ORDER BY created_at DESC LIMIT 100')
        
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entry = {
                'id': row[0],
                'transaction_id': row[1],
                'account_name': row[2],
                'account_type': row[3],
                'debit_amount': row[4],
                'credit_amount': row[5],
                'description': row[6],
                'created_at': row[7]
            }
            entries.append(entry)
        
        return entries

# Global database instance
db = Database()

