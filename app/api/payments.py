from flask import Blueprint, jsonify, request
from app.models.payment import Payment
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.user import User
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import stripe
import os
import requests

payments_bp = Blueprint('payments', __name__)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def get_currency_from_ip(ip_address):
    try:
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            currency = data.get('currency')
            if currency:
                return currency
    except Exception:
        pass
    return 'USD'

@payments_bp.route('/suggested-currency', methods=['GET'])
def suggested_currency():
    client_ip = request.remote_addr
    if client_ip == '127.0.0.1' or client_ip is None:
        return jsonify({'currency': 'USD'}), 200
    currency = get_currency_from_ip(client_ip)
    return jsonify({'currency': currency}), 200

@payments_bp.route('/checkout', methods=['POST'])
@jwt_required()
def create_checkout():
    data = request.get_json()
    course_id = data.get('course_id')
    gateway = data.get('gateway', 'stripe') 
    
    if not course_id:
        return jsonify(message="course_id is required"), 400
        
    user_id = int(get_jwt_identity())
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify(message="Course not found"), 404
        
    client_ip = request.remote_addr
    if client_ip == '127.0.0.1' or client_ip is None:
        currency = 'USD'
    else:
        currency = get_currency_from_ip(client_ip)

    if data.get('currency'):
        currency = data['currency']

    amount = course.price

    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        gateway=gateway,
        status='pending'
    )
    db.session.add(payment)
    db.session.flush() 

    if gateway == 'stripe':
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': course.title,
                        },
                        'unit_amount': int(amount * 100), 
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:3000/cancel',
                client_reference_id=str(payment.id)
            )
            payment.transaction_id = session.id
            db.session.commit()
            return jsonify({'checkout_url': session.url, 'payment_id': payment.id}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify(error=str(e)), 500
            
    elif gateway == 'paystack':
        # Paystack API integration
        try:
            url = 'https://api.paystack.co/transaction/initialize'
            headers = {
                'Authorization': f"Bearer {os.environ.get('PAYSTACK_SECRET_KEY')}",
                'Content-Type': 'application/json'
            }
            # Paystack amount is in subunits (Kobo)
            payload = {
                'email': db.session.get(User, user_id).email,
                'amount': int(amount * 100),
                'currency': currency,
                'callback_url': 'http://localhost:3000/success',
                'metadata': {
                    'payment_id': payment.id,
                    'course_id': course_id
                }
            }
            response = requests.post(url, json=payload, headers=headers)
            res_data = response.json()
            if response.status_code == 200 and res_data.get('status'):
                payment.transaction_id = res_data['data']['reference']
                db.session.commit()
                return jsonify({'checkout_url': res_data['data']['authorization_url'], 'payment_id': payment.id}), 200
            else:
                return jsonify(error="Paystack initialization failed", details=res_data), 400
        except Exception as e:
            db.session.rollback()
            return jsonify(error=str(e)), 500
            
    elif gateway == 'flutterwave':
        # Flutterwave API integration
        try:
            url = 'https://api.flutterwave.com/v3/payments'
            headers = {
                'Authorization': f"Bearer {os.environ.get('FLW_SECRET_KEY')}",
                'Content-Type': 'application/json'
            }
            # Flutterwave uses standard units but requires tx_ref
            tx_ref = f"ziff-p-{payment.id}-{int(datetime.now(timezone.utc).timestamp())}"
            user = db.session.get(User, user_id)
            payload = {
                'tx_ref': tx_ref,
                'amount': float(amount),
                'currency': currency,
                'redirect_url': 'http://localhost:3000/success',
                'customer': {
                    'email': user.email,
                    'name': user.name
                },
                'customizations': {
                    'title': 'Ziffcode Training',
                    'description': f"Payment for {course.title}"
                },
                'meta': {
                    'payment_id': payment.id,
                    'course_id': course_id
                }
            }
            response = requests.post(url, json=payload, headers=headers)
            res_data = response.json()
            if response.status_code == 200 and res_data.get('status') == 'success':
                payment.transaction_id = tx_ref
                db.session.commit()
                return jsonify({'checkout_url': res_data['data']['link'], 'payment_id': payment.id}), 200
            else:
                return jsonify(error="Flutterwave initialization failed", details=res_data), 400
        except Exception as e:
            db.session.rollback()
            return jsonify(error=str(e)), 500

    return jsonify(message="Unsupported gateway"), 400

@payments_bp.route('/verify-paystack', methods=['GET'])
@jwt_required()
def verify_paystack():
    reference = request.args.get('reference')
    if not reference:
        return jsonify(message="Reference is required"), 400
        
    try:
        url = f'https://api.paystack.co/transaction/verify/{reference}'
        headers = {
            'Authorization': f"Bearer {os.environ.get('PAYSTACK_SECRET_KEY')}"
        }
        response = requests.get(url, headers=headers)
        res_data = response.json()
        
        if response.status_code == 200 and res_data.get('status') and res_data['data']['status'] == 'success':
            # Update payment & enrollment
            payment = db.session.execute(db.select(Payment).filter_by(transaction_id=reference)).scalar_one_or_none()
            if payment:
                payment.status = 'successful'
                # Find enrollment
                course_id = res_data['data']['metadata'].get('course_id')
                enrollment = db.session.execute(
                    db.select(Enrollment).filter_by(user_id=payment.user_id, course_id=course_id)
                ).scalar_one_or_none()
                
                if enrollment:
                    enrollment.payment_status = 'Paid'
                
                db.session.commit()
                return jsonify(message="Payment verified successfully", enrollment_id=enrollment.id if enrollment else None), 200
            return jsonify(message="Payment record not found"), 404
        else:
            return jsonify(message="Payment verification failed", details=res_data), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

@payments_bp.route('/verify-flutterwave', methods=['GET'])
@jwt_required()
def verify_flutterwave():
    transaction_id = request.args.get('transaction_id')
    if not transaction_id:
        return jsonify(message="Transaction ID is required"), 400
        
    try:
        url = f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify'
        headers = {
            'Authorization': f"Bearer {os.environ.get('FLW_SECRET_KEY')}"
        }
        response = requests.get(url, headers=headers)
        res_data = response.json()
        
        if response.status_code == 200 and res_data.get('status') == 'success' and res_data['data']['status'] == 'successful':
            tx_ref = res_data['data']['tx_ref']
            payment = db.session.execute(db.select(Payment).filter_by(transaction_id=tx_ref)).scalar_one_or_none()
            
            if payment:
                payment.status = 'successful'
                course_id = res_data['data']['meta'].get('course_id')
                enrollment = db.session.execute(
                    db.select(Enrollment).filter_by(user_id=payment.user_id, course_id=course_id)
                ).scalar_one_or_none()
                
                if enrollment:
                    enrollment.payment_status = 'Paid'
                
                db.session.commit()
                return jsonify(message="Payment verified successfully", enrollment_id=enrollment.id if enrollment else None), 200
            return jsonify(message="Payment record not found"), 404
        else:
            return jsonify(message="Payment verification failed", details=res_data), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# WEBHOOKS FOR ROBUST AUTOMATION
import hmac
import hashlib

@payments_bp.route('/webhook/paystack', methods=['POST'])
def paystack_webhook():
    # Verify Paystack signature
    secret = os.environ.get('PAYSTACK_SECRET_KEY')
    signature = request.headers.get('x-paystack-signature')
    
    if not signature:
        return jsonify(status="error", message="Missing signature"), 400
        
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        request.data,
        hashlib.sha512
    ).hexdigest()
    
    if computed_signature != signature:
        return jsonify(status="error", message="Invalid signature"), 400
        
    event = request.json
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data['reference']
        
        payment = db.session.execute(db.select(Payment).filter_by(transaction_id=reference)).scalar_one_or_none()
        if payment:
            payment.status = 'successful'
            course_id = data['metadata'].get('course_id')
            enrollment = db.session.execute(
                db.select(Enrollment).filter_by(user_id=payment.user_id, course_id=course_id)
            ).scalar_one_or_none()
            
            if enrollment:
                enrollment.payment_status = 'Paid'
            
            db.session.commit()
            return jsonify(status="success"), 200
            
    return jsonify(status="ignored"), 200

@payments_bp.route('/webhook/flutterwave', methods=['POST'])
def flutterwave_webhook():
    # Flutterwave optionally uses a secret hash set in the dashboard
    secret_hash = os.environ.get('FLW_WEBHOOK_HASH') # Should be set in dashboard and .env
    signature = request.headers.get('verif-hash')
    
    if secret_hash and signature != secret_hash:
        return jsonify(status="error", message="Invalid hash"), 400
        
    event = request.json
    if event['event'] == 'charge.completed':
        data = event['data']
        if data['status'] == 'successful':
            tx_ref = data['tx_ref']
            payment = db.session.execute(db.select(Payment).filter_by(transaction_id=tx_ref)).scalar_one_or_none()
            if payment:
                payment.status = 'successful'
                # Flutterwave meta is flattened in webhooks sometimes
                course_id = data.get('meta', {}).get('course_id')
                enrollment = db.session.execute(
                    db.select(Enrollment).filter_by(user_id=payment.user_id, course_id=course_id)
                ).scalar_one_or_none()
                
                if enrollment:
                    enrollment.payment_status = 'Paid'
                
                db.session.commit()
                return jsonify(status="success"), 200
                
    return jsonify(status="ignored"), 200
