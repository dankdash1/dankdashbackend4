from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import math
import json
from src.models.order import db, Order, DeliveryPartner, OrderDelivery
from src.models.customer import Customer
from src.routes.email_routes import send_email
from src.routes.twilio_routes import send_sms

dispatch_bp = Blueprint('dispatch', __name__)

class DispatchSystem:
    """Automated dispatch system for driver assignment and routing"""
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates (Haversine formula)"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    @staticmethod
    def find_nearest_driver(delivery_location, max_distance=10):
        """Find the nearest available driver within max_distance miles"""
        try:
            # Parse delivery location (assuming format: "lat,lng")
            if isinstance(delivery_location, str):
                delivery_coords = delivery_location.split(',')
                if len(delivery_coords) != 2:
                    return None
                delivery_lat = float(delivery_coords[0])
                delivery_lng = float(delivery_coords[1])
            else:
                return None
            
            # Get all available drivers
            available_drivers = DeliveryPartner.query.filter_by(status='available').all()
            
            if not available_drivers:
                return None
            
            # Calculate distances and find nearest
            driver_distances = []
            for driver in available_drivers:
                if driver.current_location:
                    driver_coords = driver.current_location.split(',')
                    if len(driver_coords) == 2:
                        driver_lat = float(driver_coords[0])
                        driver_lng = float(driver_coords[1])
                        
                        distance = DispatchSystem.calculate_distance(
                            delivery_lat, delivery_lng, driver_lat, driver_lng
                        )
                        
                        if distance <= max_distance:
                            driver_distances.append((driver, distance))
            
            if not driver_distances:
                return None
            
            # Sort by distance and return nearest
            driver_distances.sort(key=lambda x: x[1])
            return driver_distances[0][0]  # Return the driver object
            
        except Exception as e:
            print(f"Error finding nearest driver: {e}")
            return None
    
    @staticmethod
    def auto_assign_driver(order_id):
        """Automatically assign the nearest available driver to an order"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': 'Order not found'}
            
            # Only assign for delivery orders
            if order.delivery_type != 'delivery':
                return {'success': False, 'error': 'Order is not for delivery'}
            
            # Parse shipping address to get coordinates (mock implementation)
            # In a real system, you'd use a geocoding service
            delivery_location = DispatchSystem.mock_geocode(order.shipping_address)
            
            if not delivery_location:
                return {'success': False, 'error': 'Could not geocode delivery address'}
            
            # Find nearest driver
            nearest_driver = DispatchSystem.find_nearest_driver(delivery_location)
            
            if not nearest_driver:
                return {'success': False, 'error': 'No available drivers found'}
            
            # Create delivery assignment
            delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
            if not delivery:
                delivery = OrderDelivery(order_id=order_id)
            
            delivery.partner_id = nearest_driver.id
            delivery.delivery_status = 'assigned'
            delivery.pickup_location = "34.0522,-118.2437"  # Store location (mock)
            delivery.delivery_location = delivery_location
            
            # Update driver status
            nearest_driver.status = 'busy'
            
            # Update order
            order.fulfillment_status = 'assigned_for_delivery'
            order.driver_id = nearest_driver.id
            
            # Set estimated delivery time based on distance
            distance = DispatchSystem.calculate_distance(
                34.0522, -118.2437,  # Store location
                float(delivery_location.split(',')[0]),
                float(delivery_location.split(',')[1])
            )
            
            # Estimate 30 minutes + 5 minutes per mile
            estimated_minutes = 30 + (distance * 5)
            order.estimated_delivery = datetime.now() + timedelta(minutes=estimated_minutes)
            
            db.session.add(delivery)
            db.session.commit()
            
            # Send notifications
            DispatchSystem.notify_driver(nearest_driver, order)
            DispatchSystem.notify_customer(order, nearest_driver)
            
            return {
                'success': True,
                'driver': nearest_driver.to_dict(),
                'estimated_delivery': order.estimated_delivery.isoformat(),
                'distance': round(distance, 2)
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def mock_geocode(address_json):
        """Mock geocoding function - in production, use Google Maps API or similar"""
        try:
            if isinstance(address_json, str):
                address = json.loads(address_json)
            else:
                address = address_json
            
            # Mock coordinates for different cities (in a real system, use geocoding API)
            city_coords = {
                'los angeles': '34.0522,-118.2437',
                'san francisco': '37.7749,-122.4194',
                'san diego': '32.7157,-117.1611',
                'sacramento': '38.5816,-121.4944',
                'fresno': '36.7378,-119.7871'
            }
            
            city = address.get('city', '').lower()
            return city_coords.get(city, '34.0522,-118.2437')  # Default to LA
            
        except Exception as e:
            print(f"Error geocoding address: {e}")
            return '34.0522,-118.2437'  # Default coordinates
    
    @staticmethod
    def notify_driver(driver, order):
        """Send notification to assigned driver"""
        try:
            # Send email notification
            subject = f"New Delivery Assignment - Order {order.order_number}"
            html_content = f"""
            <html>
            <body>
                <h2>New Delivery Assignment</h2>
                <p>Hi {driver.name},</p>
                <p>You have been assigned a new delivery:</p>
                <ul>
                    <li><strong>Order #:</strong> {order.order_number}</li>
                    <li><strong>Customer:</strong> {order.customer_name}</li>
                    <li><strong>Delivery Address:</strong> {json.loads(order.shipping_address).get('address', 'N/A')}</li>
                    <li><strong>Phone:</strong> {order.customer_phone}</li>
                    <li><strong>Total:</strong> ${order.total}</li>
                    <li><strong>Estimated Delivery:</strong> {order.estimated_delivery.strftime('%I:%M %p') if order.estimated_delivery else 'ASAP'}</li>
                </ul>
                <p>Please confirm receipt of this assignment and update your status in the driver app.</p>
                <p>Thank you!</p>
            </body>
            </html>
            """
            
            send_email(driver.email, subject, html_content)
            
            # Send SMS notification
            sms_message = f"DankDash: New delivery assigned! Order {order.order_number} to {order.customer_name}. Check email for details."
            send_sms(driver.phone, sms_message)
            
        except Exception as e:
            print(f"Error notifying driver: {e}")
    
    @staticmethod
    def notify_customer(order, driver):
        """Send notification to customer about driver assignment"""
        try:
            subject = f"Driver Assigned - Order {order.order_number}"
            html_content = f"""
            <html>
            <body>
                <h2>Driver Assigned to Your Order</h2>
                <p>Hi {order.customer_name},</p>
                <p>Great news! A driver has been assigned to deliver your order:</p>
                <ul>
                    <li><strong>Order #:</strong> {order.order_number}</li>
                    <li><strong>Driver:</strong> {driver.name}</li>
                    <li><strong>Vehicle:</strong> {driver.vehicle_type}</li>
                    <li><strong>Rating:</strong> {driver.rating}/5.0 ⭐</li>
                    <li><strong>Estimated Delivery:</strong> {order.estimated_delivery.strftime('%I:%M %p') if order.estimated_delivery else 'ASAP'}</li>
                </ul>
                <p>You will receive updates as your order progresses.</p>
                <p>Thank you for choosing DankDash!</p>
            </body>
            </html>
            """
            
            send_email(order.customer_email, subject, html_content)
            
            # Send SMS if customer consents
            if order.customer_phone:
                sms_message = f"DankDash: Driver {driver.name} assigned to order {order.order_number}. ETA: {order.estimated_delivery.strftime('%I:%M %p') if order.estimated_delivery else 'ASAP'}"
                send_sms(order.customer_phone, sms_message)
                
        except Exception as e:
            print(f"Error notifying customer: {e}")

@dispatch_bp.route('/dispatch/auto-assign/<int:order_id>', methods=['POST'])
def auto_assign_order(order_id):
    """Automatically assign an order to the nearest driver"""
    try:
        result = DispatchSystem.auto_assign_driver(order_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Driver assigned successfully',
                'assignment': result
            })
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dispatch_bp.route('/dispatch/available-drivers', methods=['GET'])
def get_available_drivers():
    """Get all available drivers with their locations"""
    try:
        drivers = DeliveryPartner.query.filter_by(status='available').all()
        return jsonify({
            'success': True,
            'drivers': [driver.to_dict() for driver in drivers]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dispatch_bp.route('/dispatch/driver-location/<int:driver_id>', methods=['PUT'])
def update_driver_location(driver_id):
    """Update driver's current location"""
    try:
        driver = DeliveryPartner.query.get_or_404(driver_id)
        data = request.get_json()
        
        if 'latitude' in data and 'longitude' in data:
            driver.current_location = f"{data['latitude']},{data['longitude']}"
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Location updated successfully'
            })
        else:
            return jsonify({'error': 'Latitude and longitude required'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dispatch_bp.route('/dispatch/delivery-status/<int:delivery_id>', methods=['PUT'])
def update_delivery_status(delivery_id):
    """Update delivery status"""
    try:
        delivery = OrderDelivery.query.get_or_404(delivery_id)
        data = request.get_json()
        
        old_status = delivery.delivery_status
        new_status = data.get('status')
        
        if new_status:
            delivery.delivery_status = new_status
            delivery.updated_at = datetime.utcnow()
            
            # Update timestamps based on status
            if new_status == 'picked_up':
                delivery.pickup_time = datetime.utcnow()
            elif new_status == 'delivered':
                delivery.delivery_time = datetime.utcnow()
                # Free up the driver
                if delivery.partner:
                    delivery.partner.status = 'available'
                    delivery.partner.total_deliveries += 1
                # Update order status
                delivery.order.status = 'delivered'
                delivery.order.fulfillment_status = 'delivered'
            
            if 'notes' in data:
                delivery.delivery_notes = data['notes']
            
            if 'current_location' in data:
                delivery.current_location = data['current_location']
            
            db.session.commit()
            
            # Send status update notifications
            send_delivery_status_update(delivery, old_status, new_status)
            
            return jsonify({
                'success': True,
                'message': 'Delivery status updated successfully',
                'delivery': delivery.to_dict()
            })
        else:
            return jsonify({'error': 'Status is required'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dispatch_bp.route('/dispatch/stats', methods=['GET'])
def get_dispatch_stats():
    """Get dispatch statistics"""
    try:
        today = datetime.now().date()
        
        # Active deliveries
        active_deliveries = OrderDelivery.query.filter(
            OrderDelivery.delivery_status.in_(['assigned', 'picked_up', 'in_transit'])
        ).count()
        
        # Available drivers
        available_drivers = DeliveryPartner.query.filter_by(status='available').count()
        
        # Busy drivers
        busy_drivers = DeliveryPartner.query.filter_by(status='busy').count()
        
        # Today's deliveries
        todays_deliveries = OrderDelivery.query.filter(
            OrderDelivery.created_at >= today
        ).count()
        
        # Completed deliveries today
        completed_today = OrderDelivery.query.filter(
            OrderDelivery.delivery_status == 'delivered',
            OrderDelivery.delivery_time >= today
        ).count()
        
        # Average delivery time (mock calculation)
        avg_delivery_time = 35  # minutes
        
        return jsonify({
            'success': True,
            'stats': {
                'active_deliveries': active_deliveries,
                'available_drivers': available_drivers,
                'busy_drivers': busy_drivers,
                'total_drivers': available_drivers + busy_drivers,
                'todays_deliveries': todays_deliveries,
                'completed_today': completed_today,
                'completion_rate': (completed_today / todays_deliveries * 100) if todays_deliveries > 0 else 0,
                'avg_delivery_time': avg_delivery_time
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_delivery_status_update(delivery, old_status, new_status):
    """Send status update notifications to customer"""
    try:
        order = delivery.order
        driver = delivery.partner
        
        status_messages = {
            'assigned': 'Your order has been assigned to a driver',
            'picked_up': 'Your order has been picked up and is on the way',
            'in_transit': 'Your order is in transit',
            'delivered': 'Your order has been delivered',
            'failed': 'There was an issue with your delivery'
        }
        
        if new_status in status_messages:
            subject = f"Order Update - {order.order_number}"
            html_content = f"""
            <html>
            <body>
                <h2>Order Status Update</h2>
                <p>Hi {order.customer_name},</p>
                <p>{status_messages[new_status]}.</p>
                <ul>
                    <li><strong>Order #:</strong> {order.order_number}</li>
                    <li><strong>Status:</strong> {new_status.replace('_', ' ').title()}</li>
                    <li><strong>Driver:</strong> {driver.name if driver else 'N/A'}</li>
                    <li><strong>Time:</strong> {datetime.now().strftime('%I:%M %p')}</li>
                </ul>
                {f"<p><strong>Notes:</strong> {delivery.delivery_notes}</p>" if delivery.delivery_notes else ""}
                <p>Thank you for choosing DankDash!</p>
            </body>
            </html>
            """
            
            send_email(order.customer_email, subject, html_content)
            
            # Send SMS update
            if order.customer_phone:
                sms_message = f"DankDash: {status_messages[new_status]} - Order {order.order_number}"
                send_sms(order.customer_phone, sms_message)
                
    except Exception as e:
        print(f"Error sending delivery status update: {e}")

