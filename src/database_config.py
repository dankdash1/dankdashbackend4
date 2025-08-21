import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

class DatabaseConfig:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///dankdash.db')
        self.is_postgres = self.database_url.startswith('postgres')
        
    def get_connection(self):
        """Get database connection based on environment"""
        if self.is_postgres:
            return self._get_postgres_connection()
        else:
            return self._get_sqlite_connection()
    
    def _get_postgres_connection(self):
        """Get PostgreSQL connection"""
        # Parse the database URL
        url = urlparse(self.database_url)
        
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            database=url.path[1:],  # Remove leading slash
            user=url.username,
            password=url.password,
            cursor_factory=RealDictCursor
        )
        return conn
    
    def _get_sqlite_connection(self):
        """Get SQLite connection"""
        db_path = os.path.join(os.path.dirname(__file__), 'dankdash.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        if self.is_postgres:
            self._init_postgres_tables()
        else:
            self._init_sqlite_tables()
    
    def _init_postgres_tables(self):
        """Initialize PostgreSQL tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id VARCHAR(255) PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_email VARCHAR(255),
                customer_phone VARCHAR(255),
                items TEXT,
                subtotal DECIMAL(10,2),
                tax DECIMAL(10,2),
                total DECIMAL(10,2),
                payment_method VARCHAR(100),
                status VARCHAR(100) DEFAULT 'pending',
                source VARCHAR(100) DEFAULT 'website',
                billing_address TEXT,
                shipping_address TEXT,
                fulfillment_method VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # POS Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pos_transactions (
                id SERIAL PRIMARY KEY,
                sale_id VARCHAR(255) UNIQUE,
                customer_name VARCHAR(255),
                customer_email VARCHAR(255),
                customer_phone VARCHAR(255),
                items TEXT,
                subtotal DECIMAL(10,2),
                tax DECIMAL(10,2),
                total DECIMAL(10,2),
                payment_method VARCHAR(100),
                amount_paid DECIMAL(10,2),
                change_given DECIMAL(10,2),
                status VARCHAR(100) DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(255),
                category VARCHAR(100),
                stock_quantity INTEGER,
                price DECIMAL(10,2),
                thc_content DECIMAL(5,2),
                cbd_content DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Accounting entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounting_entries (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(255),
                account_name VARCHAR(255),
                debit DECIMAL(10,2),
                credit DECIMAL(10,2),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(255),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Partners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partners (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(255),
                application_data TEXT,
                status VARCHAR(100) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("PostgreSQL tables initialized successfully")
    
    def _init_sqlite_tables(self):
        """Initialize SQLite tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                items TEXT,
                subtotal REAL,
                tax REAL,
                total REAL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                source TEXT DEFAULT 'website',
                billing_address TEXT,
                shipping_address TEXT,
                fulfillment_method TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # POS Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pos_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id TEXT UNIQUE,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                items TEXT,
                subtotal REAL,
                tax REAL,
                total REAL,
                payment_method TEXT,
                amount_paid REAL,
                change_given REAL,
                status TEXT DEFAULT 'completed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                category TEXT,
                stock_quantity INTEGER,
                price REAL,
                thc_content REAL,
                cbd_content REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Accounting entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounting_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                account_name TEXT,
                debit REAL,
                credit REAL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Partners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                application_data TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("SQLite tables initialized successfully")

# Global database config instance
db_config = DatabaseConfig()

