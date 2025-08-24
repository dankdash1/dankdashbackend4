import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.order import Order, DeliveryPartner, OrderDelivery
from src.models.customer import Customer, CustomerDocument, AccountingEntry
from src.routes.user import user_bp
from src.routes.twilio_routes import twilio_bp
from src.routes.email_routes import email_bp
from src.routes.database_order_routes import database_order_bp
from src.routes.auth_routes import auth_bp
from src.routes.customer_routes import customer_bp
from src.routes.pos_routes import pos_bp
from src.routes.pos_integration_routes import pos_integration_bp
from src.routes.dispatch_routes import dispatch_bp
from src.routes.partner_routes import partner_bp
from src.routes.test_routes import test_bp
from src.routes.dashboard_routes import dashboard_bp
from src.routes.enhanced_pos_routes import enhanced_pos_bp
from src.routes.order_management_routes import order_management_bp
from src.routes.voice_ai_routes import voice_ai_bp
from src.routes.device_routes import device_bp
from src.routes.inventory_test import inventory_test_bp
from src.database_config import db_config

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for frontend Railway domain
CORS(app, origins=[
    "https://*.up.railway.app",
    "http://localhost:3000",
    "http://localhost:5173", 
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174"
])

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(twilio_bp)
app.register_blueprint(email_bp)
app.register_blueprint(database_order_bp)
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(customer_bp, url_prefix='/api')
app.register_blueprint(pos_bp, url_prefix='/api')
app.register_blueprint(pos_integration_bp, url_prefix='/api')
app.register_blueprint(dispatch_bp, url_prefix='/api')
app.register_blueprint(partner_bp, url_prefix='/api')
app.register_blueprint(test_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(enhanced_pos_bp, url_prefix='/api/pos')
app.register_blueprint(order_management_bp, url_prefix='/api')
app.register_blueprint(voice_ai_bp, url_prefix='/api')
app.register_blueprint(device_bp, url_prefix='/api')
app.register_blueprint(inventory_test_bp, url_prefix='/api')

# PostgreSQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    try:
        # Test database connection
        conn = db_config.get_connection()
        conn.close()
        
        db.create_all()
        # Initialize database tables for PostgreSQL
        db_config.init_database()
        
        print(f"✓ PostgreSQL database connected successfully")
        print(f"✓ Database URL: {os.environ.get('DATABASE_URL', 'Not set')}")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
