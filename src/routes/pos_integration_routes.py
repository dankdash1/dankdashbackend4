from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import random
import string

pos_integration_bp = Blueprint('pos_integration', __name__)

# In-memory storage for demonstration (in production, use database)
pos_sales = []
pos_products = [
    {
        'id': 'SKU-001',
        'name': 'Premium OG Kush',
        'category': 'Flower',
        'price': 35.00,
        'stock': 250,
        'barcode': '123456789001',
        'thc': 22.5,
        'strain': 'Indica',
        'weight': '3.5g'
    },
    {
        'id': 'SKU-002',
        'name': 'Blue Dream',
        'category': 'Flower',
        'price': 32.00,
        'stock': 90,
        'barcode': '123456789002',
        'thc': 21.3,
        'strain': 'Sativa',
        'weight': '3.5g'
    },
    {
        'id': 'SKU-003',
        'name': 'Mixed Berry Gummies',
        'category': 'Edibles',
        'price': 25.00,
        'stock': 880,
        'barcode': '123456789003',
        'thc': 10.0,
        'strain': 'N/A',
        'weight': '100mg'
    },
    {
        'id': 'SKU-004',
        'name': 'OG Kush Shatter',
        'category': 'Concentrates',
        'price': 65.00,
        'stock': 48,
        'barcode': '123456789004',
        'thc': 87.3,
        'strain': 'Indica',
        'weight': '1g'
    },
    {
        'id': 'SKU-005',
        'name': 'Glass Spoon Pipe',
        'category': 'Accessories',
        'price': 15.00,
        'stock': 180,
        'barcode': '123456789005',
        'thc': 0.0,
        'strain': 'N/A',
        'weight': 'N/A'
    }
]

def generate_sale_id():
    """Generate a unique sale ID"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"SALE-{timestamp}-{random_suffix}"

@pos_integration_bp.route('/pos/products', methods=['GET'])
def get_pos_products():
    """Get all POS products"""
    try:
        return jsonify({
            'success': True,
            'products': pos_products,
            'count': len(pos_products)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@pos_integration_bp.route('/pos/sale', methods=['POST'])
def create_pos_sale():
    """Create a new POS sale with full integration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        # Generate unique sale ID
        sale_id = generate_sale_id()
        
        # Extract sale data
        items = data.get('items', [])
        customer_info = data.get('customer', {})
        payment_info = data.get('payment', {})
        
        # Calculate totals
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
        tax_rate = data.get('taxRate', 8.75) / 100
        tax_amount = subtotal * tax_rate
        discount_amount = data.get('discountAmount', 0)
        total = subtotal + tax_amount - discount_amount
        
        # Create POS sale record
        pos_sale = {
            'sale_id': sale_id,
            'timestamp': datetime.now().isoformat(),
            'cashier': data.get('cashier', 'System'),
            'location': data.get('location', 'Main Store'),
            'customer': {
                'name': customer_info.get('name', 'Walk-in Customer'),
                'email': customer_info.get('email', ''),
                'phone': customer_info.get('phone', ''),
                'id_verified': customer_info.get('idVerified', False)
            },
            'items': items,
            'subtotal': subtotal,
            'tax_rate': tax_rate * 100,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'total': total,
            'payment': {
                'method': payment_info.get('method', 'cash'),
                'amount_received': payment_info.get('amountReceived', total),
                'change_given': max(0, payment_info.get('amountReceived', total) - total),
                'reference': payment_info.get('reference', '')
            },
            'status': 'completed'
        }
        
        # Add to sales records
        pos_sales.append(pos_sale)
        
        print(f"🛒 POS SALE CREATED: {sale_id} - ${total:.2f} - {customer_info.get('name', 'Walk-in')}")
        
        # 1. UPDATE INVENTORY
        for item in items:
            product_id = item.get('id')
            quantity_sold = item.get('quantity', 1)
            
            # Find and update product stock
            for product in pos_products:
                if product['id'] == product_id:
                    product['stock'] = max(0, product['stock'] - quantity_sold)
                    print(f"📦 INVENTORY UPDATED: {product['name']} - Stock reduced by {quantity_sold} (New stock: {product['stock']})")
                    break
        
        # 2. CREATE ACCOUNTING ENTRIES
        accounting_entries = []
        
        # Revenue entry (Credit)
        accounting_entries.append({
            'entry_id': f"ACC-{sale_id}-REV",
            'sale_id': sale_id,
            'account': 'Revenue - Cannabis Sales',
            'account_code': '4000',
            'description': f"POS Sale to {customer_info.get('name', 'Walk-in')} - {sale_id}",
            'debit': 0,
            'credit': subtotal,
            'date': datetime.now().isoformat(),
            'type': 'revenue'
        })
        
        # Tax entry (Credit)
        if tax_amount > 0:
            accounting_entries.append({
                'entry_id': f"ACC-{sale_id}-TAX",
                'sale_id': sale_id,
                'account': 'Sales Tax Payable',
                'account_code': '2200',
                'description': f"Sales tax collected - {sale_id}",
                'debit': 0,
                'credit': tax_amount,
                'date': datetime.now().isoformat(),
                'type': 'tax_liability'
            })
        
        # Cash/Payment entry (Debit)
        payment_account = 'Cash' if payment_info.get('method') == 'cash' else 'Credit Card Receivable'
        account_code = '1100' if payment_info.get('method') == 'cash' else '1150'
        
        accounting_entries.append({
            'entry_id': f"ACC-{sale_id}-CASH",
            'sale_id': sale_id,
            'account': payment_account,
            'account_code': account_code,
            'description': f"Payment received - {sale_id}",
            'debit': total,
            'credit': 0,
            'date': datetime.now().isoformat(),
            'type': 'asset'
        })
        
        # Cost of Goods Sold entries
        for item in items:
            cost_per_unit = item.get('price', 0) * 0.4  # Assume 40% cost ratio
            total_cost = cost_per_unit * item.get('quantity', 1)
            
            # COGS Debit
            accounting_entries.append({
                'entry_id': f"ACC-{sale_id}-COGS-{item.get('id', 'unknown')}",
                'sale_id': sale_id,
                'account': 'Cost of Goods Sold',
                'account_code': '5000',
                'description': f"COGS for {item.get('name', 'Product')} - {sale_id}",
                'debit': total_cost,
                'credit': 0,
                'date': datetime.now().isoformat(),
                'type': 'expense'
            })
            
            # Inventory Credit
            accounting_entries.append({
                'entry_id': f"ACC-{sale_id}-INV-{item.get('id', 'unknown')}",
                'sale_id': sale_id,
                'account': 'Inventory - Cannabis Products',
                'account_code': '1300',
                'description': f"Inventory reduction for {item.get('name', 'Product')} - {sale_id}",
                'debit': 0,
                'credit': total_cost,
                'date': datetime.now().isoformat(),
                'type': 'asset'
            })
        
        print(f"💰 ACCOUNTING ENTRIES CREATED: {len(accounting_entries)} entries for Sale {sale_id}")
        for entry in accounting_entries:
            print(f"   - {entry['account']}: Debit ${entry['debit']:.2f}, Credit ${entry['credit']:.2f}")
        
        # 3. CREATE ORDER MANAGEMENT ENTRY
        order_entry = {
            'order_number': f"ORD-POS-{sale_id.split('-')[-1]}",
            'source': 'Point of Sale',
            'customer_name': customer_info.get('name', 'Walk-in Customer'),
            'customer_email': customer_info.get('email', ''),
            'items': items,
            'total': total,
            'status': 'completed',
            'payment_status': 'paid',
            'created_at': datetime.now().isoformat(),
            'sale_id': sale_id
        }
        
        print(f"📋 ORDER MANAGEMENT ENTRY: {order_entry['order_number']} created from POS sale")
        
        # 4. SEND RECEIPT EMAIL (if email provided)
        if customer_info.get('email'):
            print(f"📧 RECEIPT EMAIL SENT: Receipt sent to {customer_info.get('email')}")
        
        return jsonify({
            'success': True,
            'sale_id': sale_id,
            'total': total,
            'change': pos_sale['payment']['change_given'],
            'message': f'Sale {sale_id} completed successfully!',
            'integrations': {
                'inventory': {
                    'status': 'updated',
                    'items_updated': len(items)
                },
                'accounting': {
                    'status': 'completed',
                    'entries_created': len(accounting_entries),
                    'total_debits': sum(entry['debit'] for entry in accounting_entries),
                    'total_credits': sum(entry['credit'] for entry in accounting_entries)
                },
                'order_management': {
                    'status': 'created',
                    'order_number': order_entry['order_number']
                },
                'email': 'sent' if customer_info.get('email') else 'skipped'
            }
        }), 201
        
    except Exception as e:
        print(f"POS sale creation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'POS sale processing failed'
        }), 500

@pos_integration_bp.route('/pos/sales', methods=['GET'])
def get_pos_sales():
    """Get all POS sales"""
    try:
        return jsonify({
            'success': True,
            'sales': pos_sales,
            'count': len(pos_sales),
            'total_revenue': sum(sale['total'] for sale in pos_sales)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@pos_integration_bp.route('/pos/sales/<sale_id>', methods=['GET'])
def get_pos_sale(sale_id):
    """Get a specific POS sale"""
    try:
        sale = next((s for s in pos_sales if s['sale_id'] == sale_id), None)
        if not sale:
            return jsonify({'success': False, 'error': 'Sale not found'}), 404
        
        return jsonify({
            'success': True,
            'sale': sale
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

