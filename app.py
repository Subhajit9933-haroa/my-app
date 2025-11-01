import os
import json
import socket
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from jinja2 import DictLoader
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

# ==============================================================================
#  основных настроек (App Configuration)
# ==============================================================================

UPLOAD_FOLDER = 'uploads'
app = Flask(__name__)

# Use environment variables for configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-fallback-secret-key-for-dev')
# Render provides a DATABASE_URL for PostgreSQL. Fallback to SQLite for local dev.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///foodify.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='eventlet')

# Admin credentials from environment variables
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'SUBHAJIT')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '8167')

# ==============================================================================
# Модели базы данных (Database Models)
# ==============================================================================

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.String(255), nullable=False)
    total_bill = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class AppSetting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=True)

# ==============================================================================
# HTML и CSS шаблоны (HTML & CSS Templates)
# ==============================================================================

# --- Base Template with Header, Footer, and Styling ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}FOODIFY{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Arial', sans-serif; background-color: #ebe6c7; }
        .navbar { background-color: #198754; } /* Green */
        .navbar-brand, .nav-link { color: white !important; }
        .navbar-brand { font-weight: bold; font-size: 1.5rem; }
        .card { border: 1px solid #198754; }
        .card-title { color: #198754; }
        .btn-primary, .btn-success { background-color: #198754; border-color: #198754; }
        .btn-primary:hover, .btn-success:hover { background-color: #157347; border-color: #146c43; } /* Darker Green */
        .notification {
            position: fixed;
            top: 80px;
            right: 20px;
            background-color: #28a745;
            color: white;
            padding: 15px;
            border-radius: 5px;
            z-index: 1050;
            display: none;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    </style>
    {% block head_extra %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                {% if settings.logo_url %}
                    <img src="{{ settings.logo_url }}" alt="Foodify Logo" style="height: 40px;">
                {% else %}
                    FOODIFY 🍴
                {% endif %}
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Home</a></li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('cart_page') }}">
                            Cart <span class="badge bg-light text-dark">{{ session.get('cart')|length if session.get('cart') else 0 }}</span>
                        </a>
                    </li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('admin_login') }}">Admin</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4 mb-5">
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

# --- Homepage Template ---
HOME_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Home - FOODIFY{% endblock %}
{% block content %}
    <!-- Carousel Banner -->
    {% if foods %}
    <div id="foodCarousel" class="carousel slide mb-5" data-bs-ride="carousel">
        <div class="carousel-indicators">
            {% for food in foods %}
            <button type="button" data-bs-target="#foodCarousel" data-bs-slide-to="{{ loop.index0 }}" class="{{ 'active' if loop.first }}" aria-current="true" aria-label="Slide {{ loop.index }}"></button>
            {% endfor %}
        </div>
        <div class="carousel-inner" style="border-radius: 15px; max-height: 400px;">
            {% for food in foods %}
            <div class="carousel-item {{ 'active' if loop.first }}">
                <img src="{{ food.image_url }}" class="d-block w-100" alt="{{ food.name }}" style="object-fit: cover; height: 400px;">
                <div class="carousel-caption d-none d-md-block bg-dark bg-opacity-50 p-2 rounded">
                    <h5>{{ food.name }}</h5>
                    <p>Only Rs {{ "%.2f"|format(food.price) }}</p>
                </div>
            </div>
            {% endfor %}
        </div>
        <button class="carousel-control-prev" type="button" data-bs-target="#foodCarousel" data-bs-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Previous</span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#foodCarousel" data-bs-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Next</span>
        </button>
    </div>
    {% endif %}
    <div class="text-center mb-4">
        <h1>Welcome to FOODIFY</h1>
        <p class="lead">The best food, delivered right to your door.</p>
    </div>
    <div class="row">
        {% for food in foods %}
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <img src="{{ food.image_url }}" class="card-img-top" alt="{{ food.name }}" style="height: 200px; object-fit: cover;">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">{{ food.name }}</h5>
                    <p class="card-text">Price: Rs {{ "%.2f"|format(food.price) }}</p>
                    <form action="{{ url_for('add_to_cart', food_id=food.id) }}" method="post" class="mt-auto">
                        <div class="input-group">
                            <input type="number" name="quantity" class="form-control" value="1" min="1">
                            <button type="submit" class="btn btn-primary">Add to Cart</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% else %}
        <p>No food items available at the moment. Please check back later.</p>
        {% endfor %}
    </div>
{% endblock %}
"""

# --- Order Page Template ---
CART_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Your Cart - FOODIFY{% endblock %}
{% block content %}
<h1 class="text-center mb-4">Your Cart & Checkout</h1>
{% if error %}
    <div class="alert alert-danger">{{ error }}</div>
{% endif %}
<form id="checkoutForm" method="post" action="{{ url_for('place_order') }}">
    <div class="row">
        <!-- Cart Items -->
        <div class="col-md-6">
            <h2>Order Summary</h2>
            {% if cart_items %}
                <ul class="list-group mb-3">
                    {% for item in cart_items %}
                    <li class="list-group-item d-flex justify-content-between lh-sm">
                        <div>
                            <h6 class="my-0">{{ item.food.name }}</h6>
                            <small class="text-muted">Quantity: {{ item.quantity }}</small>
                        </div>
                        <span class="text-muted">Rs {{ "%.2f"|format(item.subtotal) }}</span>
                    </li>
                    {% endfor %}
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Total (INR)</span>
                        <strong>Rs {{ "%.2f"|format(total_bill) }}</strong>
                    </li>
                </ul>
                <a href="{{ url_for('clear_cart') }}" class="btn btn-sm btn-danger">Clear Cart</a>
            {% else %}
                <p>Your cart is empty.</p>
                <a href="{{ url_for('index') }}" class="btn btn-primary">Continue Shopping</a>
            {% endif %}
        </div>
        <!-- Customer Details -->
        {% if cart_items %}
        <div class="col-md-6">
            <h2>Delivery Details</h2>
            <div class="mb-3">
                <label for="customer_name" class="form-label">Full Name</label>
                <input type="text" class="form-control" id="customer_name" name="customer_name" required>
            </div>
            <div class="mb-3">
                <label for="customer_phone" class="form-label">Mobile Number</label>
                <input type="tel" class="form-control" id="customer_phone" name="customer_phone" required>
            </div>
            <div class="mb-3">
                <label for="customer_address" class="form-label">Delivery Address</label>
                <textarea class="form-control" id="customer_address" name="customer_address" rows="2" required></textarea>
                <button type="button" id="getLocationBtn" class="btn btn-secondary btn-sm mt-2">Auto-detect Address</button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="pincode" class="form-label">PIN Code</label>
                    <input type="text" class="form-control" id="pincode" name="pincode" required>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="landmark" class="form-label">Landmark</label>
                    <input type="text" class="form-control" id="landmark" name="landmark" placeholder="near school, club, etc.">
                </div>
            </div>
            <button type="submit" class="btn btn-success w-100 mt-3">Place Order</button>
        </div>
        {% endif %}
    </div>
</form>
{% endblock %}
{% block scripts %}
<script>
    // Geolocation
    document.getElementById('getLocationBtn').addEventListener('click', function() {
        if (navigator.geolocation) {
            this.textContent = 'Detecting...';
            this.disabled = true;
            navigator.geolocation.getCurrentPosition(position => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                // Using a free reverse geocoding service for demo purposes
                fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('customer_address').value = data.display_name || 'Could not find address.';
                        this.textContent = 'Auto-detect Address';
                        this.disabled = false;
                    })
                    .catch(() => {
                        document.getElementById('customer_address').value = `Lat: ${lat}, Lon: ${lon}. (Could not fetch address)`;
                        this.textContent = 'Auto-detect Address';
                        this.disabled = false;
                    });
            }, () => {
                alert('Geolocation failed or was denied.');
                this.textContent = 'Auto-detect Address';
                this.disabled = false;
            });
        } else {
            alert('Geolocation is not supported by your browser.');
        }
    });
</script>
{% endblock %}
"""

# --- Order Success Template ---
ORDER_SUCCESS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Order Confirmed - FOODIFY{% endblock %}
{% block content %}
<div class="text-center">
    <h1 class="text-success">✅ Order Placed Successfully!</h1>
    <p class="lead">Thank you for your order, {{ order.customer_name }}.</p>
    <div class="card w-75 mx-auto my-4">
        <div class="card-header">
            Order Summary (ID: #{{ order.id }})
        </div>
        <div class="card-body text-start">
            <p><strong>Name:</strong> {{ order.customer_name }}</p>
            <p><strong>Phone:</strong> {{ order.customer_phone }}</p>
            <p><strong>Address:</strong> {{ order.customer_address }}</p>
            <hr>
            <h6>Items:</h6>
            <ul>
            {% for item in order.items %}
                <li>{{ item.food_name }} x {{ item.quantity }} - Rs {{ "%.2f"|format(item.price * item.quantity) }}</li>
            {% endfor %}
            </ul>
            <hr>
            <h5 class="text-end">Total Bill: Rs {{ "%.2f"|format(order.total_bill) }}</h5>
        </div>
    </div>
    <a href="{{ url_for('index') }}" class="btn btn-primary">Back to Home</a>
</div>
{% endblock %}
"""

# --- Admin Login Template ---
ADMIN_LOGIN_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Admin Login - FOODIFY{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <h1 class="text-center">Admin Login</h1>
        {% if error %}
            <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form method="post">
            <div class="mb-3">
                <label for="username" class="form-label">Username</label>
                <input type="text" class="form-control" id="username" name="username" required>
            </div>
            <div class="mb-3">
                <label for="password" class="form-label">Password</label>
                <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100">Login</button>
        </form>
    </div>
</div>
{% endblock %}
"""

# --- Admin Dashboard Template ---
ADMIN_DASHBOARD_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Admin Dashboard - FOODIFY{% endblock %}
{% block head_extra %}
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Admin Dashboard</h1>
    <a href="{{ url_for('admin_logout') }}" class="btn btn-danger">Logout</a>
</div>

<!-- Site Settings Section -->
<div class="card mb-4">
    <div class="card-header">
        <h5>Site Settings</h5>
    </div>
    <div class="card-body">
        <form action="{{ url_for('admin_settings') }}" method="post" enctype="multipart/form-data">
            <div class="row align-items-center">
                <div class="col-md-2">
                    <label for="logo_file" class="form-label">Site Logo</label>
                    {% if settings.logo_url %}
                        <img src="{{ settings.logo_url }}" class="img-thumbnail" alt="Current Logo">
                    {% else %}
                        <p class="text-muted">No logo set.</p>
                    {% endif %}
                </div>
                <div class="col-md-7">
                    <input type="file" class="form-control" id="logo_file" name="logo_file">
                    <small class="form-text text-muted">Upload a new logo. Recommended height: 40px.</small>
                </div>
                <div class="col-md-3">
                    <button type="submit" class="btn btn-primary w-100">Save Settings</button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Notification Popup -->
<div id="notification" class="notification">
    <strong>New Order!</strong> A new order has been placed.
</div>

<div class="row">
    <!-- Manage Foods Section -->
    <div class="col-md-5">
        <h2>Manage Foods</h2>
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Add/Edit Food</h5>
                <form action="{{ url_for('admin_add_edit_food') }}" method="post" enctype="multipart/form-data">
                    <input type="hidden" name="food_id" id="food_id">
                    <div class="mb-3">
                        <label for="name" class="form-label">Food Name</label>
                        <input type="text" class="form-control" id="name" name="name" required>
                    </div>
                    <div class="mb-3">
                        <label for="price" class="form-label">Price</label>
                        <input type="number" step="0.01" class="form-control" id="price" name="price" required>
                    </div>
                    <div class="mb-3">
                        <label for="image_file" class="form-label">Food Image</label>
                        <input type="file" class="form-control" id="image_file" name="image_file">
                        <small class="form-text text-muted">Leave empty if you don't want to change the image.</small>
                    </div>
                    <button type="submit" class="btn btn-success">Save Food</button>
                    <button type="button" class="btn btn-secondary" onclick="clearForm()">Clear</button>
                </form>
            </div>
        </div>
        <h3 class="mt-4">Existing Foods</h3>
        <ul class="list-group">
            {% for food in foods %}
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{ food.name }} - Rs {{ "%.2f"|format(food.price) }}
                <div>
                    <button class="btn btn-sm btn-info" onclick="editFood('{{ food.id }}', '{{ food.name }}', '{{ food.price }}')">Edit</button>
                    <a href="{{ url_for('admin_delete_food', food_id=food.id) }}" class="btn btn-sm btn-danger" onclick="return confirm('Are you sure?')">Delete</a>
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>

    <!-- View Orders Section -->
    <div class="col-md-7">
        <h2>Customer Orders</h2>
        <div id="orders-list">
            {% include 'admin_orders_partial.html' %}
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
    function clearForm() {
        document.getElementById('food_id').value = '';
        document.getElementById('name').value = '';
        document.getElementById('price').value = '';
        document.getElementById('image_file').value = '';
    }

    function editFood(id, name, price) {
        document.getElementById('food_id').value = id;
        document.getElementById('name').value = name;
        document.getElementById('price').value = price;
        window.scrollTo(0, 0);
    }

    // Socket.IO for live notifications
    document.addEventListener('DOMContentLoaded', function () {
        const socket = io();
        const notification = document.getElementById('notification');

        socket.on('new_order', function(data) {
            console.log('New order received:', data.msg);
            
            // Show notification
            notification.style.display = 'block';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 5000);

            // Refresh orders list via AJAX
            fetch("{{ url_for('admin_get_orders') }}")
                .then(response => response.text())
                .then(html => {
                    document.getElementById('orders-list').innerHTML = html;
                });
        });
    });
</script>
{% endblock %}
"""

# --- Admin Orders Partial (for AJAX refresh) ---
ADMIN_ORDERS_PARTIAL = """
{% for order in orders %}
<div class="card mb-3">
    <div class="card-header d-flex justify-content-between">
        <strong>Order #{{ order.id }}</strong>
        <span>{{ order.timestamp.strftime('%Y-%m-%d %H:%M') }}</span>
    </div>
    <div class="card-body">
        <p><strong>Customer:</strong> {{ order.customer_name }} ({{ order.customer_phone }})</p>
        <p><strong>Address:</strong> {{ order.customer_address }}</p>
        <h6>Items:</h6>
        <ul>
        {% for item in order.items %}
            <li>{{ item.food_name }} x {{ item.quantity }}</li>
        {% endfor %}
        </ul>
        <hr>
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="m-0">Total: Rs {{ "%.2f"|format(order.total_bill) }}</h5>
            <div>
                <a href="https://www.google.com/maps/search/?api=1&query={{ order.customer_address|urlencode }}" target="_blank" class="btn btn-info">View on Map</a>
                <a href="{{ url_for('download_bill', order_id=order.id) }}" class="btn btn-primary">Download Bill</a>
            </div>
        </div>
    </div>
</div>
{% else %}
<p>No orders yet.</p>
{% endfor %}
"""

# ==============================================================================
# Маршруты Flask (Flask Routes)
# ==============================================================================

# --- Template dictionary and render helper ---
TEMPLATES = {
    "base.html": BASE_TEMPLATE,
    "home.html": HOME_TEMPLATE,
    "order.html": CART_TEMPLATE, # Renamed for clarity, used by cart_page
    "order_success.html": ORDER_SUCCESS_TEMPLATE,
    "admin_login.html": ADMIN_LOGIN_TEMPLATE,
    "admin_dashboard.html": ADMIN_DASHBOARD_TEMPLATE,
    "admin_orders_partial.html": ADMIN_ORDERS_PARTIAL,
}

# --- Helper function to render templates ---
def render(template_name, **context):
    # Create a Jinja environment with a DictLoader.
    # This allows template inheritance (e.g., {% extends "base.html" %}) to work correctly
    # with templates stored as strings in a dictionary.
    jinja_env = app.jinja_env.overlay()
    jinja_env.loader = DictLoader(TEMPLATES)

    # Inject settings into all templates
    logo_setting = db.session.get(AppSetting, 'logo_url')
    logo_url = None
    if logo_setting and logo_setting.value:
        logo_url = url_for('uploaded_file', filename=logo_setting.value)
    
    context['settings'] = {'logo_url': logo_url}

    template = jinja_env.get_template(template_name)
    return template.render(**context)

# --- Customer-facing Routes ---

@app.route('/')
def index():
    all_foods = Food.query.order_by(Food.name).all()
    # Prepend the correct path for locally stored images
    for food in all_foods:
        if food.image_url and not food.image_url.startswith('http'):
            food.image_url = url_for('uploaded_file', filename=food.image_url)
    return render('home.html', foods=all_foods)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serves uploaded files."""
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/cart/add/<int:food_id>', methods=['POST'])
def add_to_cart(food_id):
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    quantity = int(request.form.get('quantity', 1))
    
    # Add or update quantity in cart
    cart[str(food_id)] = cart.get(str(food_id), 0) + quantity
    
    session.modified = True
    return redirect(url_for('index'))

@app.route('/cart')
def cart_page():
    cart = session.get('cart', {})
    cart_items = []
    total_bill = 0
    
    for food_id, quantity in cart.items():
        food = Food.query.get(food_id)
        if food:
            subtotal = food.price * quantity
            cart_items.append({'food': food, 'quantity': quantity, 'subtotal': subtotal})
            total_bill += subtotal
            
    return render('order.html', cart_items=cart_items, total_bill=total_bill, error=request.args.get('error'))

@app.route('/cart/clear')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart_page'))

@app.route('/place_order', methods=['POST'])
def place_order():
    # PIN Code Validation
    pincode = request.form.get('pincode', '').strip()
    if pincode != '743425':
        error_msg = "Our order service is not available in this location."
        return redirect(url_for('cart_page', error=error_msg))

    # Extract form data
    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    full_address = request.form.get('customer_address')
    landmark = request.form.get('landmark')
    
    # Combine address parts
    delivery_address = f"{full_address}, Landmark: {landmark}, PIN: {pincode}"

    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('cart_page'))

    total_bill = 0
    order_items = []
    
    for food_id, quantity in cart.items():
        food = Food.query.get(food_id)
        if food and quantity > 0:
            total_bill += food.price * quantity
            order_items.append(OrderItem(
                food_name=food.name,
                quantity=quantity,
                price=food.price
            ))

    if not order_items:
        return redirect(url_for('cart_page'))

    # Create new order
    new_order = Order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=delivery_address,
        total_bill=total_bill,
        items=order_items
    )
    db.session.add(new_order)
    db.session.commit()

    session.pop('cart', None) # Clear cart after order
    socketio.emit('new_order', {'msg': f'New order #{new_order.id} placed!'}, namespace='/')
    return redirect(url_for('order_success', order_id=new_order.id))

@app.route('/order/success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render('order_success.html', order=order)

# --- Admin Routes ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            
    return render('admin_login.html', error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login', error=request.args.get('error')))
    
    foods = Food.query.order_by(Food.name).all()
    orders = Order.query.order_by(Order.timestamp.desc()).all()
    for food in foods:
        if food.image_url and not food.image_url.startswith('http'):
            food.image_url = url_for('uploaded_file', filename=food.image_url)
    return render('admin_dashboard.html', foods=foods, orders=orders, error=request.args.get('error'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/food', methods=['POST'])
def admin_add_edit_food():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    food_id = request.form.get('food_id')
    name = request.form.get('name')
    price = float(request.form.get('price'))
    image_file = request.files.get('image_file')

    filename = None
    if image_file and image_file.filename != '':
        filename = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if food_id: # Edit existing food
        food = Food.query.get(food_id)
        food.name = name
        food.price = price
        if filename:
            # Optionally, delete the old file
            # if food.image_url and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], food.image_url)):
            #     os.remove(os.path.join(app.config['UPLOAD_FOLDER'], food.image_url))
            food.image_url = filename
    else: # Add new food
        if not filename: # Image is required for new food
            # You might want to add an error message here
            return redirect(url_for('admin_dashboard', error="An image is required when adding a new food item."))
        new_food = Food(name=name, price=price, image_url=filename)
        db.session.add(new_food)
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/food/delete/<int:food_id>')
def admin_delete_food(food_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    food = Food.query.get_or_404(food_id)
    db.session.delete(food)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/settings', methods=['POST'])
def admin_settings():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename != '':
        filename = secure_filename(f"logo_{datetime.now().timestamp()}{os.path.splitext(logo_file.filename)[1]}")
        logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Update setting in DB
        logo_setting = db.session.get(AppSetting, 'logo_url')
        if logo_setting:
            logo_setting.value = filename
        else:
            logo_setting = AppSetting(key='logo_url', value=filename)
            db.session.add(logo_setting)
        db.session.commit()

    return redirect(url_for('admin_dashboard'))

# --- AJAX and Bill Download Routes ---

@app.route('/admin/orders')
def admin_get_orders():
    """Endpoint for AJAX to fetch updated orders list."""
    if 'admin_logged_in' not in session:
        return "Unauthorized", 401
    orders = Order.query.order_by(Order.timestamp.desc()).all()
    return render('admin_orders_partial.html', orders=orders)

@app.route('/download-bill/<int:order_id>')
def download_bill(order_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    order = Order.query.get_or_404(order_id)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Title
    elements.append(Paragraph("FOODIFY Invoice", styles['h1']))
    elements.append(Spacer(1, 12))
    
    # Order Details
    elements.append(Paragraph(f"<b>Order ID:</b> #{order.id}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date:</b> {order.timestamp.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Customer:</b> {order.customer_name}", styles['Normal']))
    elements.append(Paragraph(f"<b>Phone:</b> {order.customer_phone}", styles['Normal']))
    elements.append(Paragraph(f"<b>Address:</b> {order.customer_address}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Items Table
    data = [['Item', 'Quantity', 'Unit Price', 'Total']]
    for item in order.items:
        data.append([item.food_name, item.quantity, f"Rs {item.price:.2f}", f"Rs {item.price * item.quantity:.2f}"])
    
    data.append(['', '', '<b>Total Bill</b>', f"<b>Rs {order.total_bill:.2f}</b>"])
    
    table = Table(data, colWidths=[200, 80, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1AD145")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, -1), (-1, -1), 12),
    ]))
    elements.append(table)
    
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'bill_order_{order.id}.pdf', mimetype='application/pdf')

# ==============================================================================
# Запуск приложения (Application Runner)
# ==============================================================================

def setup_database(app):
    with app.app_context():
        # Create upload folder if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        db.create_all()
        # Add some initial food items if the database is empty.
        # This is good for first-time setup.
        if Food.query.count() == 0:
            print("Database is empty. Seeding with initial food items...")
            foods = [
                Food(name='Classic Burger', price=8.99, image_url='https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500'),
                Food(name='Margherita Pizza', price=12.50, image_url='https://images.unsplash.com/photo-1598021680133-eb3a110d4c1c?auto=format&fit=crop&w=500'),
                Food(name='Crispy Fries', price=4.00, image_url='https://images.unsplash.com/photo-1576107232684-c7e3e37b6929?auto=format&fit=crop&w=500'),
                Food(name='Caesar Salad', price=9.25, image_url='https://images.unsplash.com/photo-1550304943-4f24f54ddde9?auto=format&fit=crop&w=500')
            ]
            db.session.bulk_save_objects(foods)
            db.session.commit()
        print("Database initialized and sample data checked.")

def get_local_ip():
    """Function to get the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1' # Fallback
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    # This will create the database and tables if they don't exist
    # before the server starts.
    setup_database(app)
    print("Starting FOODIFY server... Access it at http://127.0.0.1:5000 or your local IP.")
    socketio.run(app, host="0.0.0.0", port=5000)

@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables and seeds initial data."""
    setup_database(app)
    print("Database initialized.")
