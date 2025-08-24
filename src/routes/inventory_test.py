from flask import Blueprint, jsonify

inventory_test_bp = Blueprint('inventory_test', __name__)

@inventory_test_bp.route('/inventory-test', methods=['GET'])
def test_inventory():
    return jsonify({'message': 'Inventory test route working!'}), 200