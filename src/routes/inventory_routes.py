from flask import Blueprint, request, jsonify
from src.database_config import db_config
import psycopg2
from datetime import datetime

inventory_bp = Blueprint('inventory_management', __name__)

@inventory_bp.route('/inventory/test', methods=['GET'])
def test_inventory_route():
    """Simple test route to verify inventory blueprint works"""
    return jsonify({
        'success': True,
        'message': 'Inventory blueprint is working!',
        'routes_available': ['GET /api/inventory/test', 'GET /api/inventory', 'POST /api/inventory']
    }), 200

@inventory_bp.route('/inventory', methods=['GET'])
def get_inventory():
    """Get all inventory items with optional filtering"""
    try:
        category = request.args.get('category')
        status = request.args.get('status', 'active')
        low_stock = request.args.get('low_stock', 'false').lower() == 'true'
        
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Build query based on filters
        query = """
            SELECT id, sku, name, category, subcategory, description, 
                   price, cost, stock_quantity, reserved_quantity,
                   min_stock_level, max_stock_level, unit, weight_grams,
                   thc_percentage, cbd_percentage, strain_type, brand,
                   supplier, batch_number, expiry_date, lab_tested,
                   lab_results, status, created_at, updated_at
            FROM inventory 
            WHERE status = %s
        """
        params = [status]
        
        if category:
            query += " AND category = %s"
            params.append(category)
            
        if low_stock:
            query += " AND stock_quantity <= min_stock_level"
            
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()
        
        inventory_items = []
        for item in items:
            inventory_items.append({
                'id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'category': item['category'],
                'subcategory': item['subcategory'],
                'description': item['description'],
                'price': float(item['price']) if item['price'] else None,
                'cost': float(item['cost']) if item['cost'] else None,
                'stock_quantity': item['stock_quantity'],
                'reserved_quantity': item['reserved_quantity'],
                'min_stock_level': item['min_stock_level'],
                'max_stock_level': item['max_stock_level'],
                'unit': item['unit'],
                'weight_grams': float(item['weight_grams']) if item['weight_grams'] else None,
                'thc_percentage': float(item['thc_percentage']) if item['thc_percentage'] else None,
                'cbd_percentage': float(item['cbd_percentage']) if item['cbd_percentage'] else None,
                'strain_type': item['strain_type'],
                'brand': item['brand'],
                'supplier': item['supplier'],
                'batch_number': item['batch_number'],
                'expiry_date': item['expiry_date'].isoformat() if item['expiry_date'] else None,
                'lab_tested': item['lab_tested'],
                'lab_results': item['lab_results'],
                'status': item['status'],
                'created_at': item['created_at'].isoformat(),
                'updated_at': item['updated_at'].isoformat()
            })
        
        return jsonify({
            'success': True,
            'inventory': inventory_items,
            'count': len(inventory_items),
            'filters_applied': {
                'category': category,
                'status': status,
                'low_stock_only': low_stock
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch inventory: {str(e)}'
        }), 500

@inventory_bp.route('/inventory', methods=['POST'])
def create_inventory_item():
    """Create a new inventory item"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['sku', 'name', 'category', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Check if SKU already exists
        cursor.execute("SELECT id FROM inventory WHERE sku = %s", (data['sku'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'SKU already exists'
            }), 409
        
        # Insert new inventory item
        cursor.execute("""
            INSERT INTO inventory (
                sku, name, category, subcategory, description, price, cost,
                stock_quantity, min_stock_level, max_stock_level, unit,
                weight_grams, thc_percentage, cbd_percentage, strain_type,
                brand, supplier, batch_number, expiry_date, lab_tested,
                lab_results, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id, sku, name, category, price, stock_quantity, created_at
        """, (
            data['sku'],
            data['name'],
            data['category'],
            data.get('subcategory'),
            data.get('description'),
            data['price'],
            data.get('cost'),
            data.get('stock_quantity', 0),
            data.get('min_stock_level', 5),
            data.get('max_stock_level'),
            data.get('unit', 'each'),
            data.get('weight_grams'),
            data.get('thc_percentage'),
            data.get('cbd_percentage'),
            data.get('strain_type'),
            data.get('brand'),
            data.get('supplier'),
            data.get('batch_number'),
            data.get('expiry_date'),
            data.get('lab_tested', False),
            data.get('lab_results'),
            data.get('status', 'active')
        ))
        
        item = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'item': {
                'id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'category': item['category'],
                'price': float(item['price']),
                'stock_quantity': item['stock_quantity'],
                'created_at': item['created_at'].isoformat()
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create inventory item: {str(e)}'
        }), 500

@inventory_bp.route('/inventory/<int:item_id>/adjust', methods=['POST'])
def adjust_inventory(item_id):
    """Adjust inventory stock levels (add/remove stock)"""
    try:
        data = request.get_json()
        
        if 'quantity_change' not in data:
            return jsonify({
                'success': False,
                'error': 'quantity_change is required'
            }), 400
        
        quantity_change = int(data['quantity_change'])
        adjustment_type = data.get('adjustment_type', 'manual')
        reason = data.get('reason', '')
        notes = data.get('notes', '')
        
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Get current stock
        cursor.execute("""
            SELECT stock_quantity, name FROM inventory WHERE id = %s
        """, (item_id,))
        
        item = cursor.fetchone()
        if not item:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Inventory item not found'
            }), 404
        
        current_stock = item['stock_quantity']
        new_stock = current_stock + quantity_change
        
        # Prevent negative stock
        if new_stock < 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Insufficient stock. Current: {current_stock}, Requested: {abs(quantity_change)}'
            }), 400
        
        # Update stock quantity
        cursor.execute("""
            UPDATE inventory 
            SET stock_quantity = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING stock_quantity
        """, (new_stock, item_id))
        
        updated_stock = cursor.fetchone()['stock_quantity']
        
        # Record the adjustment
        cursor.execute("""
            INSERT INTO inventory_adjustments 
            (inventory_id, adjustment_type, quantity_change, reason, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (item_id, adjustment_type, quantity_change, reason, notes))
        
        adjustment = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'adjustment': {
                'id': adjustment['id'],
                'item_name': item['name'],
                'previous_stock': current_stock,
                'quantity_change': quantity_change,
                'new_stock': updated_stock,
                'adjustment_type': adjustment_type,
                'reason': reason,
                'created_at': adjustment['created_at'].isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to adjust inventory: {str(e)}'
        }), 500

@inventory_bp.route('/inventory/low-stock', methods=['GET'])
def get_low_stock_items():
    """Get items with low stock levels"""
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sku, name, category, stock_quantity, min_stock_level,
                   (min_stock_level - stock_quantity) as shortage
            FROM inventory 
            WHERE stock_quantity <= min_stock_level 
            AND status = 'active'
            ORDER BY shortage DESC, stock_quantity ASC
        """)
        
        items = cursor.fetchall()
        conn.close()
        
        low_stock_items = []
        for item in items:
            low_stock_items.append({
                'id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'category': item['category'],
                'stock_quantity': item['stock_quantity'],
                'min_stock_level': item['min_stock_level'],
                'shortage': item['shortage']
            })
        
        return jsonify({
            'success': True,
            'low_stock_items': low_stock_items,
            'count': len(low_stock_items)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch low stock items: {str(e)}'
        }), 500