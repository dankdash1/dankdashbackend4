from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import json
import random
import string
from src.models.order import db, Order, DeliveryPartner, OrderDelivery
from src.models.user import User

order_bp = Blueprint('orders', __name__)

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"ORD-{timestamp}-{random_suffix}"

@order_bp.route('/orders', methods=['POST'])
def create_order():
    """Create a new order from checkout"""
    try:
        data = request.get_json()
        
        # Generate unique order number
        order_number = generate_order_number()
        
        # Determine delivery type based on shipping method
        shipping_method = data.get('shippingMethod', '')
        if shipping_method in ['same-day', 'next-day']:
            delivery_type = 'delivery'
        elif shipping_method == 'pickup':
            delivery_type = 'pickup'
        else:
            delivery_type = 'shipping'
        
        # Create order
        order = Order(
            order_number=order_number,
            customer_id=data.get('customerId'),
            customer_name=f"{data.get('customerInfo', {}).get('firstName', '')} {data.get('customerInfo', {}).get('lastName', '')}".strip(),
            customer_email=data.get('customerInfo', {}).get('email', ''),
            customer_phone=data.get('customerInfo', {}).get('phone', ''),
            items=json.dumps(data.get('items', [])),
            subtotal=data.get('subtotal', 0),
            shipping_cost=data.get('shippingCost', 0),
            tax_amount=data.get('taxAmount', 0),
            total=data.get('total', 0),
            shipping_address=json.dumps(data.get('shippingAddress', {})),
            billing_address=json.dumps(data.get('billingAddress', {})),
            shipping_method=shipping_method,
            delivery_type=delivery_type,
            payment_method=data.get('paymentMethod', ''),
            payment_status='pending',
            status='confirmed',
            order_notes=data.get('orderNotes', '')
        )
        
        db.session.add(order)
        db.session.commit()
        
        # Handle delivery assignment for local delivery
        if delivery_type == 'delivery':
            # Import here to avoid circular imports
            from src.routes.dispatch_routes import DispatchSystem
            dispatch_result = DispatchSystem.auto_assign_driver(order.id)
            if not dispatch_result['success']:
                print(f"Warning: Could not auto-assign driver: {dispatch_result['error']}")
        
        # Handle shipping label creation for shipped orders
        elif delivery_type == 'shipping':
            create_shipping_label(order.id, shipping_method)
        
        # Send to POS system (simulate integration)
        integrate_with_pos(order)
        
        # Send to sales module (simulate integration)
        integrate_with_sales(order)
        
        # Send order confirmation email to customer
        send_order_confirmation_email(order)
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'order_number': order_number,
            'message': 'Order created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders with filtering options"""
    try:
        # Get query parameters
        status = request.args.get('status')
        customer_email = request.args.get('customer_email')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Build query
        query = Order.query
        
        if status:
            query = query.filter(Order.status == status)
        if customer_email:
            query = query.filter(Order.customer_email.ilike(f'%{customer_email}%'))
        if date_from:
            query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))
        
        # Paginate results
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Get a specific order by ID"""
    try:
        order = Order.query.get_or_404(order_id)
        return jsonify(order.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        if 'status' in data:
            order.status = data['status']
        if 'fulfillment_status' in data:
            order.fulfillment_status = data['fulfillment_status']
        if 'tracking_number' in data:
            order.tracking_number = data['tracking_number']
        if 'internal_notes' in data:
            order.internal_notes = data['internal_notes']
        
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order status updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/delivery-partners', methods=['GET'])
def get_delivery_partners():
    """Get all delivery partners"""
    try:
        partners = DeliveryPartner.query.all()
        return jsonify([partner.to_dict() for partner in partners])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('/delivery-partners', methods=['POST'])
def create_delivery_partner():
    """Create a new delivery partner"""
    try:
        data = request.get_json()
        
        partner = DeliveryPartner(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            vehicle_type=data.get('vehicle_type'),
            license_number=data.get('license_number')
        )
        
        db.session.add(partner)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'partner_id': partner.id,
            'message': 'Delivery partner created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/orders/<int:order_id>/assign-driver', methods=['POST'])
def assign_driver(order_id):
    """Assign a driver to an order"""
    try:
        data = request.get_json()
        partner_id = data.get('partner_id')
        
        order = Order.query.get_or_404(order_id)
        partner = DeliveryPartner.query.get_or_404(partner_id)
        
        # Create or update delivery record
        delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
        if not delivery:
            delivery = OrderDelivery(order_id=order_id)
        
        delivery.partner_id = partner_id
        delivery.delivery_status = 'assigned'
        delivery.pickup_location = "Store Location"  # This would be your store's location
        delivery.delivery_location = order.shipping_address
        
        # Update partner status
        partner.status = 'busy'
        
        # Update order status
        order.fulfillment_status = 'assigned_for_delivery'
        order.driver_id = partner_id
        
        db.session.add(delivery)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Driver {partner.name} assigned to order {order.order_number}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def assign_delivery_partner(order_id, shipping_method):
    """Automatically assign an available delivery partner"""
    try:
        # Find available delivery partners
        available_partners = DeliveryPartner.query.filter_by(status='available').all()
        
        if available_partners:
            # For now, assign randomly. In production, you'd use location-based assignment
            partner = random.choice(available_partners)
            
            # Create delivery record
            delivery = OrderDelivery(
                order_id=order_id,
                partner_id=partner.id,
                delivery_status='assigned',
                pickup_location="Store Location",
                delivery_location="Customer Address"
            )
            
            # Update partner status
            partner.status = 'busy'
            
            # Update order
            order = Order.query.get(order_id)
            order.fulfillment_status = 'assigned_for_delivery'
            order.driver_id = partner.id
            
            # Set estimated delivery time
            if shipping_method == 'same-day':
                order.estimated_delivery = datetime.now() + timedelta(hours=4)
            else:  # next-day
                order.estimated_delivery = datetime.now() + timedelta(days=1)
            
            db.session.add(delivery)
            db.session.commit()
            
    except Exception as e:
        print(f"Error assigning delivery partner: {e}")

def create_shipping_label(order_id, shipping_method):
    """Create shipping label for shipped orders"""
    try:
        order = Order.query.get(order_id)
        
        # Generate tracking number
        tracking_number = f"TRK-{random.randint(100000000000, 999999999999)}"
        
        # Assign carrier based on shipping method
        if shipping_method == 'express':
            carrier = 'FedEx Express'
            estimated_days = 2
        else:  # standard
            carrier = 'USPS'
            estimated_days = 5
        
        # Update order
        order.tracking_number = tracking_number
        order.carrier = carrier
        order.fulfillment_status = 'label_created'
        order.estimated_delivery = datetime.now() + timedelta(days=estimated_days)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error creating shipping label: {e}")

def integrate_with_pos(order):
    """Integrate with POS system (placeholder for actual integration)"""
    try:
        # This would integrate with your actual POS system
        # For now, we'll just log the integration
        print(f"POS Integration: Order {order.order_number} sent to POS system")
        print(f"  - Customer: {order.customer_name}")
        print(f"  - Total: ${order.total}")
        print(f"  - Items: {len(json.loads(order.items))} items")
        
        # In a real implementation, you would:
        # 1. Send order data to POS API
        # 2. Update inventory levels
        # 3. Generate receipt
        # 4. Update accounting records
        
    except Exception as e:
        print(f"Error integrating with POS: {e}")

def integrate_with_sales(order):
    """Integrate with sales module (placeholder for actual integration)"""
    try:
        # This would integrate with your sales/CRM system
        print(f"Sales Integration: Order {order.order_number} sent to sales module")
        
        # In a real implementation, you would:
        # 1. Update customer records
        # 2. Track sales metrics
        # 3. Update commission calculations
        # 4. Trigger follow-up campaigns
        
    except Exception as e:
        print(f"Error integrating with sales: {e}")



def send_order_confirmation_email(order):
    """Send order confirmation email to customer"""
    try:
        from src.routes.email_routes import send_email
        import json
        
        # Parse items
        items = json.loads(order.items) if order.items else []
        
        # Build items HTML
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.get('name', 'Unknown Item')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item.get('quantity', 1)}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">${item.get('price', 0):.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">${(item.get('quantity', 1) * item.get('price', 0)):.2f}</td>
            </tr>
            """
        
        # Parse shipping address
        shipping_address = json.loads(order.shipping_address) if order.shipping_address else {}
        address_text = f"{shipping_address.get('address', '')}, {shipping_address.get('city', '')}, {shipping_address.get('state', '')} {shipping_address.get('zip_code', '')}"
        
        subject = f"Order Confirmation - {order.order_number}"
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .order-details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th {{ background-color: #f0f0f0; padding: 10px; text-align: left; }}
                .total-row {{ font-weight: bold; background-color: #f0f0f0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Order Confirmation</h1>
                    <p>Thank you for your order!</p>
                </div>
                
                <div class="content">
                    <div class="order-details">
                        <h2>Order Details</h2>
                        <p><strong>Order Number:</strong> {order.order_number}</p>
                        <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Customer:</strong> {order.customer_name}</p>
                        <p><strong>Email:</strong> {order.customer_email}</p>
                        <p><strong>Phone:</strong> {order.customer_phone}</p>
                    </div>
                    
                    <div class="order-details">
                        <h2>Delivery Information</h2>
                        <p><strong>Delivery Method:</strong> {order.shipping_method.replace('_', ' ').title()}</p>
                        <p><strong>Delivery Address:</strong><br>{address_text}</p>
                        {f"<p><strong>Estimated Delivery:</strong> {order.estimated_delivery.strftime('%B %d, %Y at %I:%M %p')}</p>" if order.estimated_delivery else ""}
                    </div>
                    
                    <div class="order-details">
                        <h2>Items Ordered</h2>
                        <table>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: center;">Qty</th>
                                <th style="text-align: right;">Price</th>
                                <th style="text-align: right;">Total</th>
                            </tr>
                            {items_html}
                            <tr class="total-row">
                                <td colspan="3" style="padding: 8px; text-align: right;">Subtotal:</td>
                                <td style="padding: 8px; text-align: right;">${order.subtotal:.2f}</td>
                            </tr>
                            <tr>
                                <td colspan="3" style="padding: 8px; text-align: right;">Shipping:</td>
                                <td style="padding: 8px; text-align: right;">${order.shipping_cost:.2f}</td>
                            </tr>
                            <tr>
                                <td colspan="3" style="padding: 8px; text-align: right;">Tax:</td>
                                <td style="padding: 8px; text-align: right;">${order.tax_amount:.2f}</td>
                            </tr>
                            <tr class="total-row">
                                <td colspan="3" style="padding: 8px; text-align: right; font-size: 18px;">Total:</td>
                                <td style="padding: 8px; text-align: right; font-size: 18px;">${order.total:.2f}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="order-details">
                        <h2>Payment Information</h2>
                        <p><strong>Payment Method:</strong> {order.payment_method}</p>
                        <p><strong>Payment Status:</strong> {order.payment_status.title()}</p>
                    </div>
                    
                    {f'<div class="order-details"><h2>Order Notes</h2><p>{order.order_notes}</p></div>' if order.order_notes else ''}
                    
                    <div class="order-details">
                        <h2>What's Next?</h2>
                        <ul>
                            <li>We'll process your order within 1-2 hours</li>
                            <li>You'll receive updates via email and SMS</li>
                            <li>For delivery orders, a driver will be assigned automatically</li>
                            <li>Track your order status in your account dashboard</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Questions? Contact us at support@dankdash.com or (555) 123-4567</p>
                    <p>Thank you for choosing DankDash!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        send_email(order.customer_email, subject, html_content)
        print(f"Order confirmation email sent to {order.customer_email}")
        
    except Exception as e:
        print(f"Error sending order confirmation email: {e}")

