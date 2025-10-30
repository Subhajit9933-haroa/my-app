from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
import os, json
from openpyxl import Workbook
from datetime import datetime
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
# IMPORTANT: In real-world applications, store this key in an environment variable.
app.secret_key = "fooddeliverysecretkey_subhajit" 

# -------------------- CONFIGURATION --------------------
DELIVERY_CHARGE = 20 
DEFAULT_RINGTONE = "data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjI5LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAUAAAiSAAODg4ODg4ODg4ODh4eHh4eHh4eHh4uLi4uLi4uLi4uPj4+Pj4+Pj4+Pj5OTk5OTk5OTk5OXl5eXl5eXl5eXm5ubm5ubm5ubm5+fn5+fn5+fn5+jo6Ojo6Ojo6Ojp6enp6enp6enp6urq6urq6urq6uvr6+vr6+vr6+vr7Ozs7Ozs7Ozs7O3t7e3t7e3t7e3u7u7u7u7u7u7u7+/v7+/v7+/v7+//8AAAAATGF2YzU4LjU0AAAAAAAAAAAAAAAAJAAAAAAAAAAAIkgPYLiYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTMu//MUZAYAAAGkAAAAAAAAA0gAAAAAOTku//MUZAkAAAGkAAAAAAAAA0gAAAAANVVV"

os.makedirs("data", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

PRODUCT_FILE = "data/products.json"
ORDER_FILE = "data/orders.json"
CONFIG_FILE = "data/config.json"
# Updated Default Logo with FOODIFY Theme
DEFAULT_LOGO = "https://placehold.co/150x40/4CAF50/ffffff?text=FOODIFY"

# Create files if they don't exist
if not os.path.exists(PRODUCT_FILE):
    default_products = [{
        "name": "Classic Burger",
        "price": 250,
        "quantity": 10,
        "image": "https://placehold.co/160x120/4CAF50/ffffff?text=Burger"
    }]
    with open(PRODUCT_FILE, "w") as f:
        json.dump(default_products, f, indent=2)
        
if not os.path.exists(ORDER_FILE):
    with open(ORDER_FILE, "w") as f:
        json.dump([], f, indent=2)

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "logo_url": DEFAULT_LOGO,
            "notification_sound": "/static/default_notification.mp3"  # Update this path
        }, f, indent=2)

# -------------------- HELPER FUNCTIONS --------------------
def load_json(path):
    """Loads data from a JSON file, handling empty/missing files."""
    try:
        with open(path, 'r') as f: 
            # Check if the file is empty before attempting to load
            content = f.read()
            if not content:
                print(f"Warning: {path} is empty. Returning empty list.")
                return []
            f.seek(0) # Reset file pointer to the beginning
            return json.loads(content)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        # If file exists but is corrupted JSON (e.g., 'Expecting value')
        print(f"Error: {path} contains corrupted JSON. Returning empty list.")
        return []

def save_json(path, data):
    """Saves data to a JSON file."""
    with open(path, "w") as f: 
        json.dump(data, f, indent=2) # Ensure 'f' is passed to json.dump

def load_config():
    """Loads configuration data."""
    try:
        with open(CONFIG_FILE) as f: 
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"logo_url": DEFAULT_LOGO}

def save_config(config_data):
    """Saves configuration data."""
    with open(CONFIG_FILE, "w") as f: 
        json.dump(config_data, f, indent=2)

def get_order_by_id(order_id):
    """Finds an order by its ID."""
    orders = load_json(ORDER_FILE)
    return next((o for o in orders if o["id"] == order_id), None)

# -------------------- HTML TEMPLATES (All in English) --------------------

# ১. HOME PAGE TEMPLATE
home_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FOODIFY</title>
<link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
<style>
/* Green Theme Colors */
:root {
    --primary-color: #4CAF50; /* Green 500 */
    --primary-dark: #388E3C; /* Green 700 */
    --light-accent: #E8F5E9; /* Green 50 */
    --red-alert: #F44336;
}
body { font-family:'Poppins',sans-serif;margin:0;background:#f8f8f8;color:#333; }
header { 
    background:var(--primary-color);
    color:white;
    padding:15px;
    text-align:center;
    font-size:24px;
    font-weight:bold;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60px;
}
header img { 
    height: 40px; 
    vertical-align: middle; 
    border-radius: 4px;
    max-width: 90%;
}
.nav { 
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding: 10px 20px;
    background:white;
    box-shadow:0 2px 4px rgba(0,0,0,0.05); 
}
.nav a { 
    color:var(--primary-color);
    font-weight:600;
    text-decoration:none;
    padding:5px 10px;
    border-radius:5px;
    transition: background 0.2s; 
    margin-right: 15px;
}
.nav a:hover { background: var(--light-accent); }
.container { padding:20px;text-align:center; }
.product-grid { display:flex;flex-wrap:wrap;gap:20px;justify-content:center; }
.product-card { 
    background:white;
    box-shadow:0 4px 12px rgba(0,0,0,0.1);
    border-radius:12px;
    padding:15px;
    width:200px;
    text-align:center;
    transition:transform 0.3s, box-shadow 0.3s; 
    overflow:hidden;
    box-sizing: border-box; 
}
.product-card:hover { transform:translateY(-5px);box-shadow:0 8px 16px rgba(0,0,0,0.2); }
.product-card img { width:100%;height:140px;object-fit:cover;border-radius:8px;margin-bottom:10px;display: block; }
.product-card h3 { font-size:1.2em;margin:5px 0;color:#333; }
.product-card p { font-size:1.1em;font-weight:bold;color:var(--primary-color);margin-bottom:10px; }

button { 
    background:var(--primary-color);
    border:none;
    color:white;
    padding:10px 15px;
    border-radius:8px;
    cursor:pointer;
    font-weight:600;
    transition:background 0.2s; 
    width:100%;
}
button:hover { background:var(--primary-dark); }
.cart-btn { background:var(--primary-dark); } /* Use primary dark for contrast */

input[type="number"] { width:60px;padding:5px;border:1px solid #ccc;border-radius:5px;text-align:center;margin-right:5px; }
.out-of-stock { color:var(--red-alert);font-weight:bold;padding:10px;background:var(--light-accent);border-radius:6px; }

/* Slide Menu CSS */
.slide-menu {
    height: 100%;
    width: 0; 
    position: fixed;
    z-index: 100;
    top: 0;
    right: 0;
    background-color: var(--primary-color); 
    overflow-x: hidden;
    transition: 0.5s;
    padding-top: 60px;
    box-shadow: -5px 0 15px rgba(0,0,0,0.2);
}
.slide-menu a {
    padding: 15px 10px 15px 32px;
    text-decoration: none;
    font-size: 1.5em;
    color: white;
    display: block;
    transition: 0.3s;
    text-align: left;
    font-weight: 500;
}
.slide-menu a:hover {
    background-color: var(--primary-dark);
}
.closebtn {
    position: absolute;
    top: 0;
    right: 25px;
    font-size: 36px;
    margin-left: 50px;
    color: white;
    text-decoration: none !important;
}
.menu-icon {
    font-size: 30px;
    cursor: pointer;
    color: var(--primary-color);
    padding: 0 10px;
    line-height: 1;
}

/* --- Slideshow CSS --- */
#slideshow-wrapper {
    max-width: 800px; 
    margin: 20px auto; 
    padding: 0; 
    position: relative;
}
#slideshow {
    background: white; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
    border-radius: 12px; 
    position: relative; 
    overflow: hidden; 
    width: 100%; 
    padding-top: 56.25%; /* 16:9 Aspect Ratio */
}
.slide {
    transition: opacity 0.6s ease-in-out;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    pointer-events: none;
    border-radius: inherit; 
}
.slide.active {
    opacity: 1;
    pointer-events: auto;
}
.slide img {
    width: 100%;
    height: 100%;
    object-fit: cover; 
    display: block; 
    border-radius: inherit; 
}
#prev-btn, #next-btn {
    position: absolute; 
    top: 50%; 
    transform: translateY(-50%); 
    background: rgba(255,255,255,0.7); 
    border: none; 
    padding: 10px 15px; 
    border-radius: 50%; 
    cursor: pointer; 
    font-size: 1.2em; 
    z-index: 20; 
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    transition: background 0.2s;
    line-height: 1;
}
#prev-btn:hover, #next-btn:hover { background: rgba(255,255,255,0.9); }
#prev-btn { left: 10px; }
#next-btn { right: 10px; }

#dot-indicators {
    position: absolute; 
    bottom: 10px; 
    left: 0; 
    right: 0; 
    display: flex; 
    justify-content: center; 
    gap: 8px; 
    z-index: 20;
}
.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    transition: background-color 0.3s, transform 0.3s;
}
.dot.active-dot {
    background-color: var(--primary-color);
    transform: scale(1.2);
}

@media(max-width:600px){ 
    .product-card{
        width:calc(50% - 10px); 
        padding:10px;
        margin-bottom: 10px;
    }
    .product-grid{gap:20px 10px;} 
    header{font-size:20px;}
    .nav{padding:10px;}
    .nav a{margin-right:10px;}
    #prev-btn, #next-btn { padding: 8px 12px; font-size: 1em; }
}
</style>
</head>
<body>
<header>
    {% if logo_url and logo_url != default_logo %}
        <img src="{{logo_url}}" alt="Website Logo">
    {% else %}
        🍕 FOODIFY
    {% endif %}
</header>

<!-- Slide Menu -->
<div id="mySidenav" class="slide-menu">
  <a href="javascript:void(0)" class="closebtn" onclick="closeNav()">&times;</a>
  <a href="{{url_for('cart')}}">🛒 Cart ({{cart_count}})</a>
  <a href="{{url_for('admin_login')}}">🔑 Admin Login</a>
</div>

<div class="nav">
    <a href="{{url_for('cart')}}" style="padding: 0 10px; font-size: 1.1em; background: none; margin-right: 15px;">🛒 Cart ({{cart_count}})</a>
    <span class="menu-icon" onclick="openNav()">&#9776;</span>
</div>

<!-- --- Slideshow HTML --- -->
<div id="slideshow-wrapper">
    <div id="slideshow">
        
        {% for p in products %}
        <div class="slide{% if loop.index == 1 %} active{% endif %}">
            <img src="{{p['image']}}" alt="{{p['name']}}" onerror="this.onerror=null;this.src='https://placehold.co/800x450/333333/ffffff?text=Image+Not+Found'">
        </div>
        {% endfor %}
        
        {% if not products %}
        <div class="slide active">
            <img src="https://placehold.co/800x450/333333/ffffff?text=Add+Food+Items+in+Admin+Panel" alt="No Items">
        </div>
        {% endif %}

        
        <!-- Navigation Buttons -->
        <button id="prev-btn">
            &#10094;
        </button>
        <button id="next-btn">
            &#10095;
        </button>

        <!-- Dot Indicators -->
        <div id="dot-indicators">
        </div>
    </div>
</div>
<!-- --- Slideshow HTML End --- -->

<div class="container">
    <div class="product-grid">
    {% for p in products %}
    <div class="product-card">
        <img src="{{p['image']}}" alt="{{p['name']}}" onerror="this.onerror=null;this.src='https://placehold.co/160x120/333333/ffffff?text=Image+Missing'">
        <h3>{{p['name']}}</h3>
        <p>₹{{p['price']}}</p>
        {% if p['quantity'] > 0 %}
        <form action="/add_to_cart" method="post" style="display:flex; flex-direction:column; gap:5px; align-items:center;">
            <div style="display:flex; justify-content:center; align-items:center; width:100%;">
                <label for="qty-{{loop.index}}" style="font-weight:500;">Quantity:</label>
                <input type="number" name="qty" id="qty-{{loop.index}}" min="1" max="{{p['quantity']}}" value="1" style="flex-grow:1; max-width:80px;">
            </div>
            <input type="hidden" name="name" value="{{p['name']}}">
            <input type="hidden" name="price" value="{{p['price']}}">
            <button type="submit">Add to Cart</button>
        </form>
        {% else %}
        <p class="out-of-stock">Out of Stock</p>
        {% endif %}
    </div>
    {% endfor %}
    </div>
</div>

<script>
function openNav() {
    var width = window.innerWidth > 600 ? "35%" : "80%";
    document.getElementById("mySidenav").style.width = width;
}

function closeNav() {
    document.getElementById("mySidenav").style.width = "0";
}

// --- Slideshow JAVASCRIPT ---
window.onload = function() {
    const slides = document.querySelectorAll('.slide');
    const dotContainer = document.getElementById('dot-indicators');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    let currentSlideIndex = 0;
    let intervalId = null;
    const slideDuration = 4000; 
    
    if (slides.length === 0) {
        if(prevBtn) prevBtn.style.display = 'none';
        if(nextBtn) nextBtn.style.display = 'none';
        if(dotContainer) dotContainer.style.display = 'none';
        return; 
    }

    if (slides.length <= 1) {
        if(prevBtn) prevBtn.style.display = 'none';
        if(nextBtn) nextBtn.style.display = 'none';
    }


    function showSlide(index) {
        if (index >= slides.length) {
            currentSlideIndex = 0;
        } else if (index < 0) {
            currentSlideIndex = slides.length - 1;
        } else {
            currentSlideIndex = index;
        }

        slides.forEach(slide => {
            slide.classList.remove('active');
        });

        slides[currentSlideIndex].classList.add('active');
        updateDots();
    }

    function nextSlide() {
        showSlide(currentSlideIndex + 1);
        resetAutoAdvance();
    }

    function prevSlide() {
        showSlide(currentSlideIndex - 1);
        resetAutoAdvance();
    }

    function startAutoAdvance() {
        if (slides.length > 1) {
            intervalId = setInterval(nextSlide, slideDuration);
        }
    }

    function resetAutoAdvance() {
        clearInterval(intervalId);
        startAutoAdvance();
    }

    function createDots() {
        if (slides.length <= 1) return; 

        slides.forEach((_, index) => {
            const dot = document.createElement('span');
            dot.classList.add('dot');
            dot.dataset.index = index;
            dot.addEventListener('click', () => {
                showSlide(index);
                resetAutoAdvance();
            });
            dotContainer.appendChild(dot);
        });
    }

    function updateDots() {
        const dots = dotContainer.querySelectorAll('.dot');
        dots.forEach((dot, index) => {
            if (index === currentSlideIndex) {
                dot.classList.add('active-dot');
            } else {
                dot.classList.remove('active-dot');
            }
        });
    }

    // Initialization
    if (slides.length > 0) {
        createDots();
        if (prevBtn && nextBtn) {
            prevBtn.addEventListener('click', prevSlide);
            nextBtn.addEventListener('click', nextSlide);
        }
        showSlide(0); 
        startAutoAdvance();

        const slideshowContainer = document.getElementById('slideshow');
        if (slideshowContainer) {
            slideshowContainer.addEventListener('mouseenter', () => clearInterval(intervalId));
            slideshowContainer.addEventListener('mouseleave', resetAutoAdvance);
        }
    }
};
// --- Slideshow JAVASCRIPT End ---
</script>
</body>
</html>
"""

# ২. CART TEMPLATE
cart_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🛒 FOODIFY Cart</title>
<link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
<style>
/* Green Theme Colors */
:root {
    --primary-color: #4CAF50; /* Green 500 */
    --primary-dark: #388E3C; /* Green 700 */
    --red-alert: #F44336;
    --red-alert-dark: #D32F2F;
}
body { font-family:'Poppins',sans-serif;margin:0;background:#f8f8f8;color:#333; }
header { 
    background:var(--primary-color);
    color:white;
    padding:15px;
    text-align:center;
    font-size:24px;
    font-weight:bold;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60px;
}
header img { 
    height: 40px; 
    vertical-align: middle; 
    border-radius: 4px;
    max-width: 90%;
}
.container { padding:20px;max-width:800px;margin:20px auto;background:white;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1); }
.back-link { display:block;margin-bottom:20px;color:var(--primary-color);text-decoration:none;font-weight:600; }
.cart-item { display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #eee; }
.item-info { flex-grow:1; }
.item-total { font-weight:bold;color:var(--primary-color); }
.checkout-box { border-top:2px solid var(--primary-color);padding-top:20px;margin-top:20px; }
.total-display { font-size:1.5em;font-weight:bold;margin-bottom:5px; }
.delivery-form input, .delivery-form textarea { width:100%;padding:10px;margin-bottom:10px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box; }
button { background:var(--primary-color);border:none;color:white;padding:12px 20px;border-radius:8px;cursor:pointer;font-weight:600;transition:background 0.2s;width:100%;margin-top:10px; }
button:hover { background:var(--primary-dark); }
.remove-btn { background:var(--red-alert);padding:5px 10px;border-radius:5px;width:auto;font-weight:500; }
.remove-btn:hover { background:var(--red-alert-dark); }
</style>
</head>
<body>
<header>
    {% if logo_url and logo_url != default_logo %}
        <img src="{{logo_url}}" alt="Website Logo">
    {% else %}
        🛒 FOODIFY Cart
    {% endif %}
</header>
<div class="container">
    <a href="/" class="back-link">← Continue Shopping</a>
    {% if cart %}
        {% for item in cart %}
        <div class="cart-item">
            <div class="item-info">
                {{item['name']}} (× {{item['qty']}})
                <br>
                <small>@ ₹{{item['price']}} per item</small>
            </div>
            <div class="item-total">
                ₹{{item['price'] * item['qty']}}
            </div>
            <form action="{{url_for('remove_from_cart')}}" method="POST" style="margin-left:15px;">
                <input type="hidden" name="name" value="{{item['name']}}">
                <button type="submit" class="remove-btn">Remove</button>
            </form>
        </div>
        {% endfor %}
        
        <div class="checkout-box">
            <div class="total-display">
                Subtotal: ₹{{base_total}}
            </div>
            <!-- Delivery Charge Display -->
            <div style="font-size:1.1em; color:var(--primary-color); font-weight:600; margin-bottom:10px;">
                Delivery Charge: ₹{{delivery_charge}}
            </div>
            <!-- Grand Total Display -->
            <div class="total-display" style="font-size:1.8em; border-top: 1px dashed #ccc; padding-top: 10px;">
                Grand Total: ₹{{total}}
            </div>

            <h3>Delivery Information</h3>
            <form action="{{url_for('checkout')}}" method="POST" class="delivery-form">
                <input type="text" name="name" placeholder="Your Name (Name)" required>
                <input type="text" name="phone" placeholder="Phone Number (Phone Number)" required>
                <textarea name="address" placeholder="Delivery Address (Address)" required rows="3"></textarea>
                <input type="text" name="pincode" placeholder="Pincode (Pincode)" required>
                <input type="text" name="landmark" placeholder="Nearby Landmark (Landmark)" required>
                
                <button type="submit">Confirm Order (Grand Total: ₹{{total}})</button>
            </form>
        </div>
    {% else %}
        <h3 style="text-align:center;">Cart is Empty! Order some food.</h3>
    {% endif %}
</div>
</body>
</html>
"""

# ৩. ADMIN LOGIN TEMPLATE
admin_login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔑 Admin Login</title>
    <link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
    <style>
        /* Green Theme Colors */
        :root {
            --primary-color: #4CAF50; 
            --primary-dark: #388E3C; 
        }
        body { font-family:'Poppins',sans-serif;margin:0;background:#f8f8f8;color:#333;text-align:center;padding-top:50px; }
        .login-box { background:white;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);display:inline-block;max-width:350px;width:90%; }
        h1 { color:var(--primary-color);font-size:1.8em;margin-bottom:20px; }
        input[type="text"], input[type="password"] { width:100%;padding:12px;margin-bottom:15px;border:1px solid #ccc;border-radius:8px;box-sizing:border-box; }
        button { background:var(--primary-color);border:none;color:white;padding:12px 20px;border-radius:8px;cursor:pointer;font-weight:600;transition:background 0.2s;width:100%; }
        button:hover { background:var(--primary-dark); }
        .msg { color:red;margin-bottom:10px;font-weight:500; }
        .note { color:gray;font-size:0.9em;margin-top:10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Admin Login</h1>
        {% if msg %}<p class="msg">{{msg}}</p>{% endif %}
        <form method="POST">
            <input type="text" name="userid" placeholder="User ID" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Log In</button>
        </form>
        <p class="note">Enter your admin credentials to access the panel.</p>
    </div>
</body>
</html>
"""

# ৪. ADMIN PANEL TEMPLATE
admin_panel_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚙️ FOODIFY Admin Panel</title>
    <link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
    <style>
        /* Green Theme Colors */
        :root {
            --primary-color: #4CAF50; 
            --primary-dark: #388E3C; 
            --red-alert: #F44336;
            --blue-accent: #2196F3;
        }
        body { font-family:'Poppins',sans-serif;margin:0;background:#f8f8f8;color:#333; }
        header { 
            background:var(--primary-color);
            color:white;
            padding:15px;
            text-align:center;
            font-size:24px;
            font-weight:bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 60px;
        }
        header img { 
            height: 40px; 
            vertical-align: middle; 
            border-radius: 4px;
            max-width: 90%;
        }
        .container { padding:20px;max-width:1200px;margin:20px auto; }
        .section { background:white;padding:20px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.05);margin-bottom:30px; }
        h2 { color:var(--primary-color);border-bottom:2px solid #eee;padding-bottom:10px;margin-bottom:20px; }
        form input, form button, form select { padding:8px;margin-right:10px;border-radius:6px;border:1px solid #ccc; }
        form button { background:var(--primary-dark);color:white;border:none;cursor:pointer;transition:background 0.2s; }
        form button:hover { background:var(--primary-dark); }
        
        table { width:100%;border-collapse:collapse;margin-top:15px; }
        th, td { padding:10px;border:1px solid #ddd;text-align:left;font-size:0.9em; }
        th { background:#f4f4f4;font-weight:600; }
        .remove-btn { background:var(--red-alert); }
        .remove-btn:hover { background:#D32F2F; }
        .product-list img { width:50px;height:50px;object-fit:cover;border-radius:4px; }
        .bill-btn { background:var(--blue-accent); }
        .bill-btn:hover { background:#1976D2; }
        .upload-btn { background:#03A9F4 !important; }
        .logo-display { 
            margin-top:10px; 
            padding-top:10px; 
            border-top: 1px dashed #ccc;
        }
        .download-btn { background:#00bcd4 !important; color:white; }
    </style>
</head>
<body>
<header>
    {% if logo_url and logo_url != default_logo %}
        <img src="{{logo_url}}" alt="Website Logo">
    {% endif %}
    ⚙️ FOODIFY Admin Panel
</header>
<div class="container">
    <a href="/" style="display:inline-block; margin-bottom:20px; color:var(--primary-color); text-decoration:none;">← Go to Homepage</a>

    <!-- Change Website Logo (New Section) -->
    <div class="section">
        <h2>Change Website Logo</h2>
        <form action="{{url_for('upload_logo')}}" method="POST" enctype="multipart/form-data">
            <input type="file" name="logo_image" required accept="image/*" style="border: none;">
            <button type="submit" class="upload-btn">Upload Logo</button>
        </form>
        <div class="logo-display">
            <p>Current Logo:</p>
            <img src="{{logo_url}}" alt="Current Logo" style="max-width:150px; height:auto; border:1px solid #ccc; border-radius:8px;">
            {% if logo_url == default_logo %}
                <p style="color:gray; font-size: 0.8em; margin-top:5px;">(Showing default text logo)</p>
            {% endif %}
        </div>
    </div>

    <!-- Add Product -->
    <div class="section">
        <h2>Add Product</h2>
        <form action="{{url_for('add_product')}}" method="POST" enctype="multipart/form-data">
            <input type="text" name="name" placeholder="Product Name" required>
            <input type="number" name="price" placeholder="Price (₹)" required>
            <input type="number" name="qty" placeholder="Quantity" required>
            <input type="file" name="image" required accept="image/*" style="border: none;">
            <button type="submit">Add</button>
        </form>
    </div>

    <!-- Current Products -->
    <div class="section product-list">
        <h2>Current Products (Stock)</h2>
        <table>
            <thead>
                <tr><th>Image</th><th>Name</th><th>Price</th><th>Quantity</th><th>Action</th></tr>
            </thead>
            <tbody>
                {% for p in products %}
                <tr>
                    <td><img src="{{p['image']}}" alt="{{p['name']}}"></td>
                    <td>{{p['name']}}</td>
                    <td>₹{{p['price']}}</td>
                    <td>{{p['quantity']}}</td>
                    <td>
                        <form action="{{url_for('remove_product')}}" method="POST" style="display:inline;">
                            <input type="hidden" name="name" value="{{p['name']}}">
                            <button type="submit" class="remove-btn">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- New Orders -->
    <div class="section">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h2>New Orders</h2>
            <a href="{{url_for('download_orders')}}"><button class="download-btn">Download Excel</button></a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Status</th>
                    <th>Customer</th>
                    <th>Phone/Address</th>
                    <th>Items</th>
                    <th>Grand Total</th>
                    <th>Time</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for o in orders | reverse %}
                <tr>
                    <td>{{o['id']}}</td>
                    <td style="text-transform:capitalize;">
                        {% set st = o.get('status','new') %}
                        {% if st == 'confirmed' %}
                            <span style="color:green;font-weight:600;">Confirmed</span>
                        {% elif st == 'cancelled' %}
                            <span style="color:#f44336;font-weight:600;">Cancelled</span>
                        {% else %}
                            <span style="color:#ff9800;font-weight:600;">New</span>
                        {% endif %}
                    </td>
                    <td>{{o['name']}}<br><small>{{o['pincode']}}</small></td>
                    <td>{{o['phone']}}<br><small>{{o['address']}}, {{o['landmark']}}</small></td>
                    <td>
                        <ul>
                        {% for item in o['cart'] %}
                            <li>{{item['name']}} (x{{item['qty']}})</li>
                        {% endfor %}
                        </ul>
                    </td>
                    <td>₹{{o['total']}}</td>
                    <td>{{o.get('timestamp', 'N/A')[:10]}}</td>
                    <td>
                        <a href="{{url_for('download_bill', order_id=o['id'])}}" target="_blank">
                            <button class="bill-btn">Download Bill</button>
                        </a>
                        <form action="{{url_for('confirm_order')}}" method="POST" style="display:inline;margin-left:6px;">
                            <input type="hidden" name="order_id" value="{{o['id']}}">
                            <button type="submit" class="bill-btn" {% if o.get('status') == 'confirmed' %}disabled{% endif %}>Confirm</button>
                        </form>
                        <form action="{{url_for('cancel_order')}}" method="POST" style="display:inline;margin-left:6px;">
                            <input type="hidden" name="order_id" value="{{o['id']}}">
                            <button type="submit" class="remove-btn" {% if o.get('status') == 'cancelled' %}disabled{% endif %}>Cancel</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Notification Settings (New Section) -->
    <div class="section">
        <h2>Notification</h2>
        <p style="color:gray;">Built-in notification sound is used. Upload option removed.</p>
    </div>
</div>
<script>
let currentOrderCount = {{orders|length}};
let notificationSound = new Audio('data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjI5LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAUAAAiSAAODg4ODg4ODg4ODh4eHh4eHh4eHh4uLi4uLi4uLi4uPj4+Pj4+Pj4+Pj5OTk5OTk5OTk5OXl5eXl5eXl5eXm5ubm5ubm5ubm5+fn5+fn5+fn5+jo6Ojo6Ojo6Ojp6enp6enp6enp6urq6urq6urq6uvr6+vr6+vr6+vr7Ozs7Ozs7Ozs7O3t7e3t7e3t7e3u7u7u7u7u7u7u7+/v7+/v7+/v7+//8AAAAATGF2YzU4LjU0AAAAAAAAAAAAAAAAJAAAAAAAAAAAIkgPYLiYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTMu//MUZAYAAAGkAAAAAAAAA0gAAAAAOTku//MUZAkAAAGkAAAAAAAAA0gAAAAANVVV');
let playCount = 0;
const TOTAL_PLAYS = 40;

// Function to play notification sound
function playNotification() {
    if (playCount >= TOTAL_PLAYS) {
        playCount = 0;
        return;
    }

    notificationSound.play().then(() => {
        console.log(`Playing notification sound: ${playCount + 1}/${TOTAL_PLAYS}`);
        playCount++;
        
        // When sound ends, play again if count not reached
        notificationSound.onended = function() {
            if (playCount < TOTAL_PLAYS) {
                playNotification();
            } else {
                playCount = 0;
                notificationSound.onended = null;
            }
        };
    }).catch(error => {
        console.error("Error playing notification:", error);
    });
}

// Check for new orders
function checkNewOrders() {
    fetch('/check_new_orders')
        .then(response => response.json())
        .then(data => {
            if (data.count > currentOrderCount) {
                console.log("New order detected! Playing notification...");
                playCount = 0;  // Reset count
                playNotification();  // Start playing notifications
                
                // Update current count
                currentOrderCount = data.count;
                
                // Show browser notification
                if ("Notification" in window) {
                    Notification.requestPermission().then(permission => {
                        if (permission === "granted") {
                            new Notification("New Order!", {
                                body: "You have received a new order!"
                            });
                        }
                    });
                }
                
                // Reload page after 2 seconds
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }
        })
        .catch(error => console.error("Error checking orders:", error));
}

// Check for new orders every 5 seconds
setInterval(checkNewOrders, 5000);
</script>
</body>
</html>
"""


# -------------------- ROUTES AND VIEW FUNCTIONS (Translated Strings) --------------------

@app.route("/")
def home():
    """Displays the main product page."""
    products = load_json(PRODUCT_FILE)
    cart_count = sum(item.get("qty", 1) for item in session.get("cart", []))
    config = load_config()
    logo_url = config.get("logo_url", DEFAULT_LOGO)
    
    return render_template_string(home_html, products=products, cart_count=cart_count, logo_url=logo_url, default_logo=DEFAULT_LOGO)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """Adds a product to the shopping cart."""
    try:
        name = request.form["name"]
        price = int(request.form["price"])
        qty = int(request.form["qty"])
    except (KeyError, ValueError):
        return redirect(url_for("home"))

    if qty <= 0:
        return redirect(url_for("home"))

    cart = session.get("cart", [])
    
    found = False
    for item in cart:
        if item["name"] == name:
            item["qty"] += qty
            found = True
            break
    
    if not found:
        cart.append({"name": name, "price": price, "qty": qty})
        
    session["cart"] = cart
    return redirect(url_for("home"))

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    """Removes an item from the cart."""
    name_to_remove = request.form.get("name")
    cart = session.get("cart", [])
    updated_cart = [item for item in cart if item['name'] != name_to_remove]
    session["cart"] = updated_cart
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    """Displays the shopping cart page, calculates total including delivery charge."""
    cart = session.get("cart", [])
    base_total = sum(c["price"]*c["qty"] for c in cart)
    
    # Add delivery charge only if cart is not empty
    delivery_charge = DELIVERY_CHARGE if base_total > 0 else 0
    total = base_total + delivery_charge

    config = load_config()
    logo_url = config.get("logo_url", DEFAULT_LOGO)
    
    # Pass base_total and delivery_charge to the template
    return render_template_string(
        cart_html, 
        cart=cart, 
        base_total=base_total, 
        delivery_charge=delivery_charge, 
        total=total, 
        logo_url=logo_url, 
        default_logo=DEFAULT_LOGO
    )

@app.route("/checkout", methods=["POST"])
def checkout():
    """Processes the order, saves it, and updates inventory."""
    cart = session.get("cart", [])
    if not cart:
        return "<h2>❌ Cannot Place Order: Cart is Empty!</h2><a href='/'>Go back to Homepage</a>"
        
    try:
        base_total = sum(c["price"]*c["qty"] for c in cart)
        delivery_charge = DELIVERY_CHARGE
        total_amount = base_total + delivery_charge # Grand Total
        
        order = {
            "name": request.form["name"], 
            "phone": request.form["phone"],
            "address": request.form["address"], 
            "pincode": request.form["pincode"],
            "landmark": request.form["landmark"], 
            "cart": cart,
            "base_total": base_total,        # New: Store subtotal
            "delivery_charge": delivery_charge, # New: Store delivery charge
            "total": total_amount,          # Grand Total
            "id": datetime.now().strftime("%Y%m%d%H%M%S") + str(int(time.time() * 1000) % 10000).zfill(4), 
            "timestamp": datetime.now().isoformat()
        }
    except KeyError:
        return "<h2>❌ Delivery details are incomplete!</h2><a href='/cart'>Go back to Cart</a>"


    # 1. Update Order File (This is where the error occurred previously)
    orders = load_json(ORDER_FILE)
    orders.append(order)
    save_json(ORDER_FILE, orders)

    # 2. Update Product Inventory
    products = load_json(PRODUCT_FILE)
    product_map = {p["name"]: p for p in products}

    for item in order["cart"]:
        product_name = item["name"]
        ordered_qty = item["qty"]
        if product_name in product_map:
            product_map[product_name]["quantity"] -= ordered_qty
            if product_map[product_name]["quantity"] < 0:
                product_map[product_name]["quantity"] = 0 

    save_json(PRODUCT_FILE, products)
    
    # 3. Clear Cart
    session["cart"] = []
    
    # Updated Success Message with Green Theme and Delivery Charge Info
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Order Confirmed</title>
    <link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
    <style>
        body {{ font-family:'Poppins',sans-serif;background:#e8f5e9;color:#333;text-align:center;padding-top:100px; }}
        .box {{ background:white;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);display:inline-block; }}
        h2 {{ color:#4CAF50; font-size: 2em; }}
        p {{ font-size: 1.1em; }}
        a {{ background:#4CAF50;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:20px;display:inline-block; }}
        a:hover {{ background:#388E3C; }}
    </style>
    </head>
    <body>
        <div class="box">
            <h2>✅ Order Successful!</h2>
            <p>Your Order ID: <strong>{order['id']}</strong></p>
            <p>Grand Total: <strong>₹{order['total']}</strong> (Includes Delivery Charge of ₹{order['delivery_charge']})</p>
            <p>Your food will be delivered to your address soon.</p>
            <a href='/'>Go back to Homepage</a>
        </div>
    </body>
    </html>
    """

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    """Admin login page."""
    msg=""
    if request.method=="POST":
        if request.form["userid"]=="SUBHAJIT" and request.form["password"]=="8167":
            session["admin"]=True
            return redirect("/panel")
        else: 
            msg="Wrong ID or Password! (ভুল আইডি বা পাসওয়ার্ড!)"
    return render_template_string(admin_login_html, msg=msg)

@app.route("/panel")
def panel():
    """Admin panel dashboard."""
    if not session.get("admin"): 
        return redirect("/admin")
    products = load_json(PRODUCT_FILE)
    orders = load_json(ORDER_FILE)
    config = load_config()
    logo_url = config.get("logo_url", DEFAULT_LOGO)
    notification_sound = config.get("notification_sound", DEFAULT_RINGTONE)
    return render_template_string(
        admin_panel_html, 
        products=products, 
        orders=orders, 
        logo_url=logo_url, 
        default_logo=DEFAULT_LOGO,
        notification_sound=notification_sound
    )

@app.route("/upload_logo", methods=["POST"])
def upload_logo():
    """Uploads website logo and updates configuration."""
    if not session.get("admin"): return redirect("/admin")
    
    file = request.files.get("logo_image")
    if not file or file.filename == '':
        return "Logo file missing", 400
        
    try:
        # Securely save the file
        filename = secure_filename(file.filename)
        unique_filename = f"logo_{int(time.time())}_{filename}"
        path = os.path.join("static/uploads", unique_filename)
        file.save(path)
        logo_url = "/" + path.replace("\\", "/")
        
        config = load_config()
        config["logo_url"] = logo_url
        save_config(config)
        
    except Exception as e:
        print(f"Error uploading logo: {e}")
        return f"An error occurred: {e}", 500
        
    return redirect(url_for("panel"))


@app.route("/add_product", methods=["POST"])
def add_product():
    """Adds a new product to the inventory."""
    if not session.get("admin"): return redirect("/admin")
    
    try:
        file = request.files["image"]
        if not file:
            return "Image file missing", 400
            
        # Securely save the file
        filename = secure_filename(file.filename)
        unique_filename = f"{int(time.time())}_{filename}"
        path = os.path.join("static/uploads", unique_filename)
        file.save(path)
        image_url = "/" + path.replace("\\", "/")
        
        products = load_json(PRODUCT_FILE)
        products.append({
            "name": request.form["name"],
            "price": int(request.form["price"]),
            "quantity": int(request.form["qty"]),
            "image": image_url
        })
        save_json(PRODUCT_FILE, products)
    except Exception as e:
        print(f"Error adding product: {e}")
        return f"An error occurred: {e}", 500
        
    return redirect("/panel")

@app.route("/remove_product", methods=["POST"])
def remove_product():
    """Removes a product from the inventory."""
    if not session.get("admin"): return redirect("/admin")
    product_name = request.form.get("name")
    
    if not product_name:
        return "Product name missing.", 400
        
    products = load_json(PRODUCT_FILE)
    
    # Code to remove the product's image
    product_to_remove = next((p for p in products if p.get("name") == product_name), None)
    if product_to_remove and 'image' in product_to_remove:
        image_path = product_to_remove['image'].lstrip('/')
        full_path = os.path.join(app.root_path, image_path)
        if os.path.exists(full_path) and not full_path.endswith('placehold.co'):
            try:
                os.remove(full_path)
            except OSError as e:
                print(f"Error deleting image: {e}")
    
    updated_products = [p for p in products if p.get("name") != product_name]
    
    save_json(PRODUCT_FILE, updated_products)
    return redirect("/panel")

@app.route("/download_orders")
def download_orders():
    """Downloads all orders as an Excel file."""
    if not session.get("admin"): return redirect("/admin")
    orders = load_json(ORDER_FILE)
    
    wb = Workbook(); ws = wb.active
    # Updated Excel Columns to include Subtotal and Delivery Charge
    ws.append(["Order ID","Customer","Phone","Address","Pincode","Landmark","Items","Subtotal","Delivery Charge","Grand Total","Timestamp"])
    for o in orders:
        items = ", ".join([f"{i['name']} x{i['qty']}" for i in o["cart"]])
        # Handle new fields (base_total, delivery_charge) and fall back gracefully for old orders
        subtotal = o.get("base_total", o.get("total", 0) - o.get("delivery_charge", 0))
        delivery = o.get("delivery_charge", 0)
        grand_total = o.get("total", subtotal + delivery)

        timestamp = o.get("timestamp", "N/A") 
        # Add new fields to the row
        ws.append([o["id"],o["name"],o["phone"],o["address"],o["pincode"],o["landmark"],items, subtotal, delivery, grand_total, timestamp])
    file = "data/orders.xlsx"; wb.save(file)
    return send_file(file, as_attachment=True)

@app.route("/download_bill/<order_id>")
def download_bill(order_id):
    """Generates a simple HTML bill for packaging."""
    if not session.get("admin"): return redirect("/admin")
    order = get_order_by_id(order_id)
    if not order: return "Order not found", 404
    
    order_time_raw = order.get('timestamp', datetime.now().isoformat()) 
    try:
        order_time = datetime.fromisoformat(order_time_raw).strftime('%Y-%m-%d %I:%M %p')
    except ValueError:
        order_time = order_time_raw 
        
    # Get Subtotal and Delivery Charge from the order data
    base_total = order.get('base_total', order['total'] - order.get('delivery_charge', 0)) # Fallback
    delivery_charge = order.get('delivery_charge', 0)
    
    # Bill HTML Content (Updated with FOODIFY branding)
    bill_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Order Invoice - {order_id}</title>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 20px; }}
            .invoice {{ width: 300px; border: 2px solid #4CAF50; padding: 15px; margin: 0 auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #4CAF50; margin-bottom: 5px; font-size: 1.5em; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }}
            h2 {{ text-align: center; font-size: 1em; margin-top: 0; padding-bottom: 10px; font-weight: 400; }}
            p {{ margin: 5px 0; font-size: 0.9em; line-height: 1.3; }}
            strong {{ font-weight: 600; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 5px 0; text-align: left; font-size: 0.9em; }}
            th {{ border-bottom: 1px dashed #ccc; }}
            .total-line {{ display: flex; justify-content: space-between; margin-top: 5px; }}
            .total {{ font-weight: bold; border-top: 1px dashed #4CAF50; padding-top: 10px; font-size: 1.1em; color: #4CAF50; }}
            .footer {{ text-align: center; margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; font-size: 0.8em; }}
        </style>
    </head>
    <body onload="window.print()">
        <div class="invoice">
            <h1>FOODIFY</h1>
            <h2>Packing Slip</h2>
            
            <p><strong>Order ID:</strong> {order['id']}</p>
            <p><strong>Date/Time:</strong> {order_time}</p>
            <br>
            <p><strong>Customer:</strong> {order['name']}</p>
            <p><strong>Phone:</strong> {order['phone']}</p>
            <p><strong>Delivery Address:</strong> {order['address']}</p>
            <p><strong>Pincode:</strong> {order['pincode']}</p>
            <p><strong>Landmark:</strong> {order['landmark']}</p>
            <br>
            
            <table>
                <thead>
                    <tr><th>Item</th><th>Quantity</th><th>Price (Unit)</th></tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{item['name']}</td><td>{item['qty']}</td><td>₹{item['price']}</td></tr>" for item in order['cart']])}
                </tbody>
            </table>
            
            <div class="total-line"><p>Subtotal:</p><p>₹{base_total}</p></div>
            <div class="total-line"><p style="color:#4CAF50;">Delivery Charge:</p><p style="color:#4CAF50;">₹{delivery_charge}</p></div>
            
            <div class="total total-line">
                <p>Grand Total:</p><p>₹{order['total']}</p>
            </div>
            
            <div class="footer">
                Thank you for your order! - Call {order['phone']} for delivery (FOODIFY)
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(bill_content)

@app.route('/check_new_orders')
def check_new_orders():
    """API endpoint to check for new orders."""
    if not session.get("admin"):
        return {"error": "Unauthorized"}, 401
    
    orders = load_json(ORDER_FILE)
    return {"count": len(orders)}

@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors, especially for audio files"""
    if request.path.startswith('/static/') and request.path.endswith(('.mp3', '.wav')):
        return redirect(DEFAULT_RINGTONE)
    return e

@app.route("/confirm_order", methods=["POST"])
def confirm_order():
    """Mark an order as confirmed."""
    if not session.get("admin"):
        return redirect("/admin")
    order_id = request.form.get("order_id")
    if not order_id:
        return redirect("/panel")
    orders = load_json(ORDER_FILE)
    changed = False
    for o in orders:
        if o.get("id") == order_id:
            o["status"] = "confirmed"
            o["confirmed_at"] = datetime.now().isoformat()
            changed = True
            break
    if changed:
        save_json(ORDER_FILE, orders)
    return redirect("/panel")

@app.route("/cancel_order", methods=["POST"])
def cancel_order():
    """Mark an order as cancelled and restock items.""" 
    if not session.get("admin"):
        return redirect("/admin")
    order_id = request.form.get("order_id")
    if not order_id:
        return redirect("/panel")
    orders = load_json(ORDER_FILE)
    products = load_json(PRODUCT_FILE)
    product_map = {p["name"]: p for p in products}
    changed = False
    for o in orders:
        if o.get("id") == order_id:
            if o.get("status") == "cancelled":
                break
            # Restock items back to products
            for item in o.get("cart", []):
                name = item.get("name")
                try:
                    qty = int(item.get("qty", 0))
                except (TypeError, ValueError):
                    qty = 0
                if name in product_map:
                    product_map[name]["quantity"] = product_map[name].get("quantity", 0) + qty
            o["status"] = "cancelled"
            o["cancelled_at"] = datetime.now().isoformat()
            changed = True
            break
    if changed:
        save_json(PRODUCT_FILE, list(product_map.values()))
        save_json(ORDER_FILE, orders)
    return redirect("/panel")
# ...existing code...
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


