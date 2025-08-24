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
        
        # Drop and recreate inventory table to ensure schema is correct
        try:
            cursor.execute('DROP TABLE IF EXISTS inventory_adjustments CASCADE')
            cursor.execute('DROP TABLE IF EXISTS inventory CASCADE')
            print("✓ Dropped existing inventory tables")
        except Exception as e:
            print(f"Info: {e}")  # Table might not exist yet
        
        # Enhanced Inventory table with cannabis-specific fields
        cursor.execute('''
            CREATE TABLE inventory (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                subcategory VARCHAR(100),
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                cost DECIMAL(10,2),
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                reserved_quantity INTEGER DEFAULT 0,
                min_stock_level INTEGER DEFAULT 5,
                max_stock_level INTEGER,
                unit VARCHAR(50) DEFAULT 'each',
                weight_grams DECIMAL(10,3),
                thc_percentage DECIMAL(5,2),
                cbd_percentage DECIMAL(5,2),
                strain_type VARCHAR(50),
                brand VARCHAR(100),
                supplier VARCHAR(100),
                batch_number VARCHAR(100),
                expiry_date DATE,
                lab_tested BOOLEAN DEFAULT false,
                lab_results TEXT,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')

        # Inventory adjustments table (for tracking stock changes)
        cursor.execute('''
            CREATE TABLE inventory_adjustments (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES inventory(id) ON DELETE CASCADE,
                adjustment_type VARCHAR(50) NOT NULL,
                quantity_change INTEGER NOT NULL,
                reason VARCHAR(255),
                reference_id VARCHAR(100),
                notes TEXT,
                created_by VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW()
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

