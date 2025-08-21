from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import json
from src.models.order import db, Order
from src.models.customer import Customer, AccountingEntry
from src.routes.email_routes import send_email

pos_bp = Blueprint('pos', __name__)

class POSSystem:
    """Point of Sales system integration"""
    
    @staticmethod
    def process_sale(order_data):
        """Process a sale through the POS system"""
        try:
            # Create POS transaction record
            pos_transaction = {
                'transaction_id': f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'order_id': order_data.get('order_id'),
                'customer_id': order_data.get('customer_id'),
                'items': order_data.get('items', []),
                'subtotal': order_data.get('subtotal', 0),
                'tax': order_data.get('tax_amount', 0),
                'total': order_data.get('total', 0),
                'payment_method': order_data.get('payment_method'),
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            # Update inventory (simulate inventory management)
            POSSystem.update_inventory(order_data.get('items', []))
            
            # Create accounting entries
            POSSystem.create_accounting_entries(pos_transaction)
            
            # Generate receipt
            receipt = POSSystem.generate_receipt(pos_transaction)
            
            return {
                'success': True,
                'transaction': pos_transaction,
                'receipt': receipt
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_inventory(items):
        """Update inventory levels after sale"""
        # This would integrate with your actual inventory system
        for item in items:
            print(f"Inventory Update: {item.get('name')} - Quantity: -{item.get('quantity')}")
            # In a real system, you would:
            # 1. Reduce inventory levels
            # 2. Check for low stock alerts
            # 3. Update product availability
            # 4. Log inventory movements
    
    @staticmethod
    def create_accounting_entries(transaction):
        """Create accounting entries for the sale"""
        try:
            total = transaction['total']
            tax = transaction['tax']
            subtotal = transaction['subtotal']
            
            # Sales Revenue Entry (Credit)
            revenue_entry = AccountingEntry(
                transaction_type='sale',
                reference_type='pos_transaction',
                reference_id=transaction['transaction_id'],
                account_code='4000',
                account_name='Sales Revenue',
                debit_amount=0,
                credit_amount=subtotal,
                description=f"POS Sale - {transaction['transaction_id']}",
                customer_id=transaction.get('customer_id'),
                transaction_date=datetime.now().date()
            )
            
            # Sales Tax Entry (Credit)
            if tax > 0:
                tax_entry = AccountingEntry(
                    transaction_type='sale',
                    reference_type='pos_transaction',
                    reference_id=transaction['transaction_id'],
                    account_code='2200',
                    account_name='Sales Tax Payable',
                    debit_amount=0,
                    credit_amount=tax,
                    description=f"Sales Tax - {transaction['transaction_id']}",
                    customer_id=transaction.get('customer_id'),
                    transaction_date=datetime.now().date()
                )
                db.session.add(tax_entry)
            
            # Cash/Card Receivable Entry (Debit)
            payment_method = transaction['payment_method']
            account_code = '1100' if payment_method.lower() == 'cash' else '1150'
            account_name = 'Cash' if payment_method.lower() == 'cash' else 'Card Receivables'
            
            payment_entry = AccountingEntry(
                transaction_type='sale',
                reference_type='pos_transaction',
                reference_id=transaction['transaction_id'],
                account_code=account_code,
                account_name=account_name,
                debit_amount=total,
                credit_amount=0,
                description=f"Payment Received - {payment_method} - {transaction['transaction_id']}",
                customer_id=transaction.get('customer_id'),
                transaction_date=datetime.now().date()
            )
            
            db.session.add(revenue_entry)
            db.session.add(payment_entry)
            db.session.commit()
            
        except Exception as e:
            print(f"Error creating accounting entries: {e}")
    
    @staticmethod
    def generate_receipt(transaction):
        """Generate receipt for the transaction"""
        receipt = {
            'transaction_id': transaction['transaction_id'],
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'items': transaction['items'],
            'subtotal': transaction['subtotal'],
            'tax': transaction['tax'],
            'total': transaction['total'],
            'payment_method': transaction['payment_method'],
            'receipt_number': f"RCP-{transaction['transaction_id'][-8:]}"
        }
        
        return receipt

@pos_bp.route('/pos/sales', methods=['POST'])
def create_pos_sale():
    """Create a new POS sale"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['items', 'total', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Process the sale
        result = POSSystem.process_sale(data)
        
        if result['success']:
            # Send receipt email if customer email provided
            if data.get('customer_email'):
                send_receipt_email(data['customer_email'], result['receipt'])
            
            return jsonify({
                'success': True,
                'message': 'Sale processed successfully',
                'transaction': result['transaction'],
                'receipt': result['receipt']
            }), 201
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/sales', methods=['GET'])
def get_pos_sales():
    """Get POS sales with filtering"""
    try:
        # Get query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        payment_method = request.args.get('payment_method')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build query (using orders as POS sales for now)
        query = Order.query
        
        if date_from:
            query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))
        if payment_method:
            query = query.filter(Order.payment_method == payment_method)
        
        # Paginate results
        sales = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'sales': [sale.to_dict() for sale in sales.items],
            'total': sales.total,
            'pages': sales.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/sales/<transaction_id>', methods=['GET'])
def get_pos_sale(transaction_id):
    """Get a specific POS sale"""
    try:
        # For now, using order_number as transaction_id
        sale = Order.query.filter_by(order_number=transaction_id).first_or_404()
        return jsonify({
            'success': True,
            'sale': sale.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/refunds', methods=['POST'])
def create_refund():
    """Process a refund"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('transaction_id') or not data.get('amount'):
            return jsonify({'error': 'Transaction ID and amount are required'}), 400
        
        transaction_id = data['transaction_id']
        refund_amount = float(data['amount'])
        reason = data.get('reason', 'Customer request')
        
        # Find original transaction (using order)
        original_order = Order.query.filter_by(order_number=transaction_id).first()
        if not original_order:
            return jsonify({'error': 'Original transaction not found'}), 404
        
        # Create refund accounting entries
        create_refund_accounting_entries(original_order, refund_amount, reason)
        
        # Update order status
        original_order.status = 'refunded'
        original_order.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Send refund confirmation email
        if original_order.customer_email:
            send_refund_email(original_order.customer_email, transaction_id, refund_amount)
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'refund_amount': refund_amount,
            'transaction_id': transaction_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/stats', methods=['GET'])
def get_pos_stats():
    """Get POS statistics"""
    try:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Daily sales
        daily_sales = db.session.query(db.func.sum(Order.total)).filter(
            Order.created_at >= today
        ).scalar() or 0
        
        # Weekly sales
        weekly_sales = db.session.query(db.func.sum(Order.total)).filter(
            Order.created_at >= week_ago
        ).scalar() or 0
        
        # Monthly sales
        monthly_sales = db.session.query(db.func.sum(Order.total)).filter(
            Order.created_at >= month_ago
        ).scalar() or 0
        
        # Transaction counts
        daily_transactions = Order.query.filter(Order.created_at >= today).count()
        weekly_transactions = Order.query.filter(Order.created_at >= week_ago).count()
        monthly_transactions = Order.query.filter(Order.created_at >= month_ago).count()
        
        # Average order value
        avg_order_value = monthly_sales / monthly_transactions if monthly_transactions > 0 else 0
        
        # Top selling items (mock data for now)
        top_items = [
            {'name': 'Blue Dream - Premium Flower', 'quantity_sold': 45, 'revenue': 2025.00},
            {'name': 'Mixed Berry Gummies - 10mg', 'quantity_sold': 38, 'revenue': 836.00},
            {'name': 'OG Kush - Premium Flower', 'quantity_sold': 32, 'revenue': 1440.00}
        ]
        
        return jsonify({
            'success': True,
            'stats': {
                'daily_sales': float(daily_sales),
                'weekly_sales': float(weekly_sales),
                'monthly_sales': float(monthly_sales),
                'daily_transactions': daily_transactions,
                'weekly_transactions': weekly_transactions,
                'monthly_transactions': monthly_transactions,
                'average_order_value': float(avg_order_value),
                'top_items': top_items
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/inventory', methods=['GET'])
def get_inventory():
    """Get inventory levels"""
    try:
        # Mock inventory data - in a real system, this would come from your inventory database
        inventory = [
            {
                'id': 1,
                'name': 'Blue Dream - Premium Flower',
                'sku': 'BD-001',
                'current_stock': 25,
                'min_stock': 10,
                'max_stock': 100,
                'unit_cost': 35.00,
                'selling_price': 45.00,
                'status': 'in_stock'
            },
            {
                'id': 2,
                'name': 'Mixed Berry Gummies - 10mg',
                'sku': 'MBG-001',
                'current_stock': 5,
                'min_stock': 10,
                'max_stock': 50,
                'unit_cost': 18.00,
                'selling_price': 22.00,
                'status': 'low_stock'
            },
            {
                'id': 3,
                'name': 'OG Kush - Premium Flower',
                'sku': 'OGK-001',
                'current_stock': 0,
                'min_stock': 10,
                'max_stock': 100,
                'unit_cost': 40.00,
                'selling_price': 50.00,
                'status': 'out_of_stock'
            }
        ]
        
        return jsonify({
            'success': True,
            'inventory': inventory,
            'low_stock_count': len([item for item in inventory if item['status'] == 'low_stock']),
            'out_of_stock_count': len([item for item in inventory if item['status'] == 'out_of_stock'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/pos/inventory/<int:item_id>/adjust', methods=['POST'])
def adjust_inventory(item_id):
    """Adjust inventory levels"""
    try:
        data = request.get_json()
        adjustment = data.get('adjustment', 0)
        reason = data.get('reason', 'Manual adjustment')
        
        # In a real system, you would update the actual inventory record
        print(f"Inventory Adjustment: Item {item_id}, Adjustment: {adjustment}, Reason: {reason}")
        
        # Create accounting entry for inventory adjustment
        if adjustment != 0:
            account_code = '1300'  # Inventory Asset
            account_name = 'Inventory'
            
            entry = AccountingEntry(
                transaction_type='inventory_adjustment',
                reference_type='inventory',
                reference_id=item_id,
                account_code=account_code,
                account_name=account_name,
                debit_amount=adjustment if adjustment > 0 else 0,
                credit_amount=abs(adjustment) if adjustment < 0 else 0,
                description=f"Inventory Adjustment - {reason}",
                transaction_date=datetime.now().date()
            )
            
            db.session.add(entry)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory adjusted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def create_refund_accounting_entries(order, refund_amount, reason):
    """Create accounting entries for refunds"""
    try:
        # Refund Sales Revenue (Debit)
        revenue_entry = AccountingEntry(
            transaction_type='refund',
            reference_type='order',
            reference_id=order.id,
            account_code='4000',
            account_name='Sales Revenue',
            debit_amount=refund_amount,
            credit_amount=0,
            description=f"Refund - {order.order_number} - {reason}",
            customer_id=order.customer_id,
            transaction_date=datetime.now().date()
        )
        
        # Refund Payment (Credit)
        payment_method = order.payment_method
        account_code = '1100' if payment_method.lower() == 'cash' else '1150'
        account_name = 'Cash' if payment_method.lower() == 'cash' else 'Card Receivables'
        
        payment_entry = AccountingEntry(
            transaction_type='refund',
            reference_type='order',
            reference_id=order.id,
            account_code=account_code,
            account_name=account_name,
            debit_amount=0,
            credit_amount=refund_amount,
            description=f"Refund Payment - {payment_method} - {order.order_number}",
            customer_id=order.customer_id,
            transaction_date=datetime.now().date()
        )
        
        db.session.add(revenue_entry)
        db.session.add(payment_entry)
        
    except Exception as e:
        print(f"Error creating refund accounting entries: {e}")

def send_receipt_email(email, receipt):
    """Send receipt email to customer"""
    subject = f"Receipt - {receipt['receipt_number']}"
    
    items_html = ""
    for item in receipt['items']:
        items_html += f"""
        <tr>
            <td>{item.get('name', 'Unknown Item')}</td>
            <td>{item.get('quantity', 1)}</td>
            <td>${item.get('price', 0):.2f}</td>
            <td>${(item.get('quantity', 1) * item.get('price', 0)):.2f}</td>
        </tr>
        """
    
    html_content = f"""
    <html>
    <body>
        <h2>DankDash Receipt</h2>
        <p><strong>Receipt #:</strong> {receipt['receipt_number']}</p>
        <p><strong>Date:</strong> {receipt['date']}</p>
        <p><strong>Transaction ID:</strong> {receipt['transaction_id']}</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
            {items_html}
        </table>
        
        <p><strong>Subtotal:</strong> ${receipt['subtotal']:.2f}</p>
        <p><strong>Tax:</strong> ${receipt['tax']:.2f}</p>
        <p><strong>Total:</strong> ${receipt['total']:.2f}</p>
        <p><strong>Payment Method:</strong> {receipt['payment_method']}</p>
        
        <p>Thank you for your business!</p>
    </body>
    </html>
    """
    
    send_email(email, subject, html_content)

def send_refund_email(email, transaction_id, refund_amount):
    """Send refund confirmation email"""
    subject = f"Refund Processed - {transaction_id}"
    html_content = f"""
    <html>
    <body>
        <h2>Refund Confirmation</h2>
        <p>Your refund has been processed successfully.</p>
        <p><strong>Transaction ID:</strong> {transaction_id}</p>
        <p><strong>Refund Amount:</strong> ${refund_amount:.2f}</p>
        <p>Please allow 3-5 business days for the refund to appear in your account.</p>
        <p>Thank you for your business!</p>
    </body>
    </html>
    """
    
    send_email(email, subject, html_content)

