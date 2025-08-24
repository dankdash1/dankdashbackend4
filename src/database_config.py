import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

class DatabaseConfig:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return self._get_postgres_connection()
    
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
    
    def init_database(self):
        """Initialize PostgreSQL database tables"""
        self._init_postgres_tables()
    
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
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'offline',
                last_seen TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        conn.commit()
        conn.close()
        print("PostgreSQL tables initialized successfully")

# Global database config instance
db_config = DatabaseConfig()

