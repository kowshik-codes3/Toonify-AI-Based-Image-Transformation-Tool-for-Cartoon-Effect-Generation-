import os
import razorpay
from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from database import create_connection, get_user_profile

# Import Razorpay configuration
try:
    from razorpay_config import RAZORPAY_TEST_KEY_ID, RAZORPAY_TEST_KEY_SECRET
    print("Loaded Razorpay config from razorpay_config.py")
except ImportError:
    print("razorpay_config.py not found, using environment variables")
    RAZORPAY_TEST_KEY_ID = ""
    RAZORPAY_TEST_KEY_SECRET = ""

# Blueprint for payments
payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

# Razorpay keys (from config file or environment)
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', RAZORPAY_TEST_KEY_ID)
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', RAZORPAY_TEST_KEY_SECRET)

# Initialize client (use real keys or simulation mode)
razorpay_client = None
SIMULATE = os.getenv('RAZORPAY_SIMULATE', '0') == '1'

# For real testing, set your Razorpay test keys here or in environment variables
if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    print("Please set your Razorpay test keys in environment variables:")
    print("RAZORPAY_KEY_ID=rzp_test_your_test_key_id")
    print("RAZORPAY_KEY_SECRET=your_test_secret_key")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and not SIMULATE:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        print(f"Razorpay client initialized with test key: {RAZORPAY_KEY_ID[:12]}...")
    except Exception as e:
        print(f"Failed to initialize Razorpay client: {e}")
        razorpay_client = None


class _FakeUtility:
    def verify_payment_signature(self, params):
        # In simulation mode we accept any signature (no-op) but raise if missing keys
        required = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']
        for k in required:
            if k not in (params or {}):
                raise Exception('missing_param:' + k)
        # no exception => verification passed
        print('SIMULATION: verify_payment_signature OK', params)


class _FakeClient:
    def __init__(self):
        self.utility = _FakeUtility()

    class order:
        @staticmethod
        def create(payload):
            # return a fake order dict with an id that looks like Razorpay order id
            print('SIMULATION: creating fake order with payload', payload)
            return {'id': 'order_sim_' + str(int(os.times()[4]))}


if not razorpay_client:
    if SIMULATE:
        razorpay_client = _FakeClient()
        print('Razorpay simulation mode enabled (RAZORPAY_SIMULATE=1)')
    else:
        # Keep None — route will show an error to the user if they try to pay
        razorpay_client = None


@payments_bp.route('/create-order', methods=['POST'])
def create_order():
    # simple endpoint to create a Razorpay order and render checkout
    if 'user_email' not in session:
        flash('Please log in to make a payment.', 'error')
        return redirect(url_for('login'))

    filename = request.form.get('download_filename') or request.form.get('filename')
    image_id = request.form.get('image_id')
    # Allow overriding amount from form (in INR). Default to 50 INR
    try:
        amount_inr = int(float(request.form.get('amount_inr', 50)))
    except Exception:
        amount_inr = 50

    if not filename:
        flash('No file specified for purchase.', 'error')
        return redirect(url_for('dashboard'))
    
    if not image_id:
        flash('Image ID not specified.', 'error')
        return redirect(url_for('dashboard'))

    if not razorpay_client:
        flash('Payment gateway not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.', 'error')
        return redirect(url_for('dashboard'))

    amount_paise = amount_inr * 100
    receipt_id = f"rcpt_{session.get('user_email', 'guest')}_{int(os.times()[4])}"

    try:
        order = razorpay_client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt_id,
            'payment_capture': '1'
        })
        order_id = order.get('id')
        user_profile = get_user_profile(create_connection(), session['user_email'])
        return render_template('payment_checkout.html', key_id=RAZORPAY_KEY_ID, order_id=order_id, amount_paise=amount_paise, amount_inr=amount_inr, filename=filename, image_id=image_id, user_profile=user_profile, session=session)
    except Exception as e:
        print('Error creating Razorpay order:', e)
        flash('Could not initiate payment. Please try again later.', 'error')
        return redirect(url_for('dashboard'))


@payments_bp.route('/verify', methods=['POST'], endpoint='verify')
def verify_payment():
    # Verify Razorpay payment signature posted from client after Checkout
    if 'user_email' not in session:
        flash('Please log in to complete the payment.', 'error')
        return redirect(url_for('login'))

    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    filename = request.form.get('filename')
    image_id = request.form.get('image_id')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        flash('Missing payment details for verification.', 'error')
        return redirect(url_for('dashboard'))

    if not razorpay_client:
        flash('Payment gateway not configured.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # utility.verify_payment_signature will raise an exception if verification fails
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
        # Payment is valid - mark image as paid in database
        if image_id:
            from database import mark_image_as_paid
            conn = create_connection()
            if conn:
                success = mark_image_as_paid(conn, image_id, razorpay_payment_id, razorpay_order_id)
                conn.close()
                if success:
                    print(f"Image {image_id} marked as paid with payment {razorpay_payment_id}")
                else:
                    print(f"Failed to mark image {image_id} as paid")
        
        flash('Payment successful. Your download will begin shortly.', 'success')
        return redirect(url_for('payments.payment_success', filename=filename, image_id=image_id))
    except Exception as e:
        print('Razorpay verification failed:', e)
        flash('Payment verification failed. If amount was charged, contact support.', 'error')
        return redirect(url_for('dashboard'))


@payments_bp.route('/payment-success/<filename>')
def payment_success(filename):
    # Simple success page; in a real flow you might mark the order in DB and provide the file
    image_id = request.args.get('image_id')
    user_profile = get_user_profile(create_connection(), session.get('user_email'))
    return render_template('payment_success.html', filename=filename, image_id=image_id, user_profile=user_profile, session=session)
