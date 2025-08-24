from flask import Blueprint, request, jsonify
from src.database_config import db_config
import psycopg2
from datetime import datetime

device_bp = Blueprint('device', __name__)

@device_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices with their status and last_seen timestamp"""
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, status, last_seen 
            FROM devices 
            ORDER BY last_seen DESC
        """)
        
        devices = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for JSON response
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device['id'],
                'name': device['name'],
                'status': device['status'],
                'last_seen': device['last_seen'].isoformat() if device['last_seen'] else None
            })
        
        return jsonify({
            'success': True,
            'devices': devices_list,
            'count': len(devices_list)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch devices: {str(e)}'
        }), 500

@device_bp.route('/devices', methods=['POST'])
def create_device():
    """Create a new device by name (optional endpoint)"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Device name is required'
            }), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({
                'success': False,
                'error': 'Device name cannot be empty'
            }), 400
        
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Check if device name already exists
        cursor.execute("SELECT id FROM devices WHERE name = %s", (name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Device with this name already exists'
            }), 409
        
        # Insert new device
        cursor.execute("""
            INSERT INTO devices (name, status, last_seen) 
            VALUES (%s, 'offline', NOW()) 
            RETURNING id, name, status, last_seen
        """, (name,))
        
        device = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'device': {
                'id': device['id'],
                'name': device['name'],
                'status': device['status'],
                'last_seen': device['last_seen'].isoformat()
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create device: {str(e)}'
        }), 500

@device_bp.route('/devices/<int:device_id>/status', methods=['POST'])
def update_device_status(device_id):
    """Update device status and set last_seen to NOW()"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        status = data['status'].strip()
        if not status:
            return jsonify({
                'success': False,
                'error': 'Status cannot be empty'
            }), 400
        
        # Validate status values (optional - you can add more valid statuses)
        valid_statuses = ['online', 'offline', 'maintenance', 'error']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Valid options: {", ".join(valid_statuses)}'
            }), 400
        
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Check if device exists
        cursor.execute("SELECT id, name FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        
        if not device:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        # Update device status and last_seen
        cursor.execute("""
            UPDATE devices 
            SET status = %s, last_seen = NOW() 
            WHERE id = %s 
            RETURNING id, name, status, last_seen
        """, (status, device_id))
        
        updated_device = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'device': {
                'id': updated_device['id'],
                'name': updated_device['name'],
                'status': updated_device['status'],
                'last_seen': updated_device['last_seen'].isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update device status: {str(e)}'
        }), 500

@device_bp.route('/inventory-debug', methods=['GET'])
def debug_inventory_in_device():
    """Debug route to test if inventory can work from device blueprint"""
    return jsonify({
        'success': True,
        'message': 'Inventory debug route working from device blueprint!',
        'note': 'This proves the issue is with inventory_routes.py file'
    }), 200