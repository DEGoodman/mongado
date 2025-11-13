---
id: 12
title: "Python & Flask Refresher"
url: ""
tags: ["python", "flask", "webdev", "reference", "backend"]
draft: false
published_date: "2025-11-13T10:00:00"
created_at: "2025-11-13T10:00:00"
---

**Purpose**: Quick reference guide to refresh Python 3.13+ and Flask fundamentals

---

## Table of Contents

1. [Python Fundamentals](#python-fundamentals)
2. [Python Advanced Patterns](#python-advanced-patterns)
3. [Flask Fundamentals](#flask-fundamentals)
4. [Flask Application Structure](#flask-application-structure)
5. [Flask Advanced Patterns](#flask-advanced-patterns)
6. [Quick Reference](#quick-reference)
7. [Practice Exercises](#practice-exercises)

---

## Python Fundamentals

### Modern Type Hints (Python 3.13)

```python
# Modern Python 3.13 syntax - no imports needed
def greet(name: str, age: int | None = None) -> str:
    """Type hints built into Python 3.13."""
    if age:
        return f"Hello {name}, age {age}"
    return f"Hello {name}"

# Old style (pre-3.10) - avoid
from typing import Optional, Union, List, Dict

def old_style(value: Optional[int]) -> Union[str, int]:
    pass

# Modern style (3.13+) - use this
def modern_style(value: int | None) -> str | int:
    pass

# Collection types
def process_data(
    items: list[str],           # Not List[str]
    mapping: dict[str, int],    # Not Dict[str, int]
    values: set[int],           # Not Set[int]
    coords: tuple[int, int]     # Not Tuple[int, int]
) -> list[int]:
    return [1, 2, 3]

# Complex types
from typing import Any, Callable, Protocol

# Any - avoid when possible
def legacy_api(data: Any) -> Any:
    return data

# Callable - function types
def apply_function(func: Callable[[int, int], int]) -> int:
    return func(5, 3)

# Protocol - structural typing (like TypeScript interfaces)
class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()

# Generic types
from typing import TypeVar

T = TypeVar('T')

def get_first(items: list[T]) -> T | None:
    return items[0] if items else None

# Type aliases
ProductID = str
Price = float
Product = dict[str, Any]

def get_product(product_id: ProductID) -> Product:
    return {"id": product_id, "name": "Laptop", "price": 999.99}

# Literal types
from typing import Literal

Status = Literal["pending", "processing", "shipped", "delivered"]

def update_status(order_id: str, status: Status) -> None:
    print(f"Order {order_id} is now {status}")
```

---

### Data Classes and Pydantic

**Data classes provide clean, typed object definitions.**

```python
from dataclasses import dataclass, field
from datetime import datetime

# Basic dataclass
@dataclass
class Product:
    id: str
    name: str
    price: float
    in_stock: bool = True  # Default value

product = Product(id="1", name="Laptop", price=999.99)
print(product.name)  # "Laptop"

# With methods
@dataclass
class ShoppingCart:
    items: list[Product] = field(default_factory=list)

    def add_item(self, product: Product) -> None:
        self.items.append(product)

    def total(self) -> float:
        return sum(item.price for item in self.items)

# Frozen (immutable)
@dataclass(frozen=True)
class ImmutableProduct:
    id: str
    name: str
    price: float

# product.price = 899  # ❌ Error: frozen

# Pydantic - validation + serialization (popular with FastAPI)
from pydantic import BaseModel, Field, validator

class Product(BaseModel):
    id: str
    name: str
    price: float = Field(gt=0, description="Price must be positive")
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('name')
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1",
                "name": "Laptop",
                "price": 999.99,
                "tags": ["electronics", "computers"]
            }
        }

# Usage
product = Product(id="1", name="Laptop", price=999.99)
print(product.model_dump())  # Convert to dict
print(product.model_dump_json())  # Convert to JSON
```

---

### Context Managers

```python
# Built-in context managers
with open("file.txt", "r") as f:
    content = f.read()
# File automatically closed

# Multiple context managers
with open("input.txt") as infile, open("output.txt", "w") as outfile:
    outfile.write(infile.read())

# Custom context manager (class-based)
class DatabaseConnection:
    def __enter__(self):
        self.conn = connect_to_db()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        # Return True to suppress exceptions

with DatabaseConnection() as conn:
    conn.execute("SELECT * FROM users")

# Custom context manager (function-based)
from contextlib import contextmanager

@contextmanager
def temporary_setting(name: str, value: Any):
    old_value = get_setting(name)
    set_setting(name, value)
    try:
        yield
    finally:
        set_setting(name, old_value)

with temporary_setting("debug", True):
    # Code with debug=True
    pass
# Automatically restored to old value

# Real-world example: Database transaction
@contextmanager
def db_transaction(session):
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

with db_transaction(db_session) as session:
    session.add(new_user)
    session.add(new_order)
# Auto-commits or rolls back
```

---

### List/Dict Comprehensions and Generators

```python
# List comprehension
numbers = [1, 2, 3, 4, 5]
squares = [n**2 for n in numbers]
# [1, 4, 9, 16, 25]

# With condition
even_squares = [n**2 for n in numbers if n % 2 == 0]
# [4, 16]

# Nested comprehension
matrix = [[1, 2], [3, 4], [5, 6]]
flattened = [num for row in matrix for num in row]
# [1, 2, 3, 4, 5, 6]

# Dict comprehension
products = [
    {"id": "1", "name": "Laptop", "price": 999},
    {"id": "2", "name": "Mouse", "price": 29}
]
product_map = {p["id"]: p["name"] for p in products}
# {"1": "Laptop", "2": "Mouse"}

# Set comprehension
tags = {"python", "flask", "web", "python", "flask"}
uppercase_tags = {tag.upper() for tag in tags}
# {"PYTHON", "FLASK", "WEB"}

# Generator expression (lazy evaluation)
large_numbers = (n**2 for n in range(1000000))
# Doesn't compute all values immediately

first_five = [next(large_numbers) for _ in range(5)]
# [0, 1, 4, 9, 16]

# Generator function
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

fib = fibonacci()
print(next(fib))  # 0
print(next(fib))  # 1
print(next(fib))  # 1
print(next(fib))  # 2

# Practical example: Process large file
def read_large_file(file_path: str):
    with open(file_path) as f:
        for line in f:
            yield line.strip()

# Only loads one line at a time
for line in read_large_file("huge.txt"):
    process(line)
```

---

## Python Advanced Patterns

### Decorators

**Decorators wrap functions to modify behavior.**

```python
from functools import wraps
from time import time
from typing import Callable, Any

# Basic decorator
def timer(func: Callable) -> Callable:
    @wraps(func)  # Preserves original function metadata
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        end = time()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

@timer
def slow_function():
    # Equivalent to: slow_function = timer(slow_function)
    sum(range(1000000))

slow_function()  # Prints execution time

# Decorator with arguments
def repeat(times: int):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet(name: str):
    print(f"Hello, {name}")

greet("Alice")  # Prints 3 times

# Stacking decorators
@timer
@repeat(3)
def process_data():
    # Executes bottom-up: repeat(3) then timer
    compute_expensive_operation()

# Class-based decorator
class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            self.calls = [c for c in self.calls if now - c < self.period]

            if len(self.calls) >= self.max_calls:
                raise Exception("Rate limit exceeded")

            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper

@RateLimiter(max_calls=5, period=60)
def api_call():
    return fetch_data()

# Common Flask decorators
from flask import abort

def require_admin(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    return wrapper

@app.route('/admin')
@require_admin
def admin_panel():
    return "Admin panel"
```

---

### Error Handling

```python
# Basic try/except
try:
    result = risky_operation()
except ValueError as e:
    print(f"Invalid value: {e}")
except KeyError:
    print("Key not found")
except Exception as e:
    # Catch all other exceptions
    print(f"Unexpected error: {e}")
else:
    # Runs if no exception raised
    print("Success!")
finally:
    # Always runs (cleanup)
    cleanup()

# Multiple exceptions
try:
    process_data()
except (ValueError, KeyError) as e:
    handle_error(e)

# Raising exceptions
def validate_price(price: float) -> None:
    if price < 0:
        raise ValueError(f"Price must be positive, got {price}")
    if price > 1000000:
        raise ValueError("Price too high")

# Custom exceptions
class ProductNotFoundError(Exception):
    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")

class InvalidPriceError(Exception):
    pass

def get_product(product_id: str) -> Product:
    if product_id not in products:
        raise ProductNotFoundError(product_id)
    return products[product_id]

# Usage
try:
    product = get_product("123")
except ProductNotFoundError as e:
    print(e.product_id)
    log_error(e)

# Context manager for error handling
from contextlib import suppress

# Suppress specific exceptions
with suppress(FileNotFoundError):
    os.remove("file.txt")
# If file doesn't exist, no error

# Re-raising exceptions
try:
    risky_operation()
except Exception as e:
    log_error(e)
    raise  # Re-raise same exception

# Exception chaining
try:
    data = fetch_data()
except RequestError as e:
    raise DataProcessingError("Failed to process") from e
    # Preserves original exception in __cause__
```

---

### Async/Await (Asyncio)

```python
import asyncio
from typing import Any

# Basic async function
async def fetch_user(user_id: str) -> dict[str, Any]:
    await asyncio.sleep(1)  # Simulate API call
    return {"id": user_id, "name": "Alice"}

# Running async function
user = asyncio.run(fetch_user("123"))

# Multiple concurrent tasks
async def fetch_multiple_users(user_ids: list[str]) -> list[dict[str, Any]]:
    # Run all requests concurrently
    tasks = [fetch_user(user_id) for user_id in user_ids]
    users = await asyncio.gather(*tasks)
    return users

# Usage
users = asyncio.run(fetch_multiple_users(["1", "2", "3"]))
# All 3 requests run concurrently (1 second total, not 3)

# Error handling in async
async def safe_fetch(url: str) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.text
    except httpx.RequestError as e:
        print(f"Error fetching {url}: {e}")
        return None

# Async context manager
class AsyncDatabaseConnection:
    async def __aenter__(self):
        self.conn = await connect_to_db()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()

async def query_database():
    async with AsyncDatabaseConnection() as conn:
        result = await conn.execute("SELECT * FROM users")
        return result

# Async iterator
class AsyncDataStream:
    async def __aiter__(self):
        for i in range(10):
            await asyncio.sleep(0.1)
            yield i

async def process_stream():
    async for item in AsyncDataStream():
        print(item)

# Flask with async (Flask 2.0+)
from flask import Flask

app = Flask(__name__)

@app.route('/users/<user_id>')
async def get_user(user_id: str):
    # Async route handler
    user = await fetch_user(user_id)
    return user
```

---

## Flask Fundamentals

### Basic Application

```python
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Basic route
@app.route('/')
def index():
    return "Hello, World!"

# Route with variable
@app.route('/user/<username>')
def show_user(username: str):
    return f"User: {username}"

# Route with type converter
@app.route('/post/<int:post_id>')
def show_post(post_id: int):
    return f"Post {post_id}"

# Multiple HTTP methods
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Process login
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# JSON API endpoint
@app.route('/api/products', methods=['GET'])
def get_products():
    products = [
        {"id": "1", "name": "Laptop", "price": 999},
        {"id": "2", "name": "Mouse", "price": 29}
    ]
    return jsonify(products)

# POST endpoint
@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()

    # Validate
    if not data or 'name' not in data:
        return jsonify({"error": "Name required"}), 400

    product = {
        "id": generate_id(),
        "name": data["name"],
        "price": data.get("price", 0)
    }

    save_product(product)
    return jsonify(product), 201

# URL parameters (query string)
@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    results = search_products(query, page)
    return jsonify(results)

# Running the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

### Request and Response

```python
from flask import (
    Flask, request, jsonify, make_response,
    redirect, url_for, abort, send_file
)

app = Flask(__name__)

# Request object
@app.route('/example', methods=['GET', 'POST'])
def example():
    # Form data
    username = request.form.get('username')

    # JSON data
    data = request.get_json()

    # Query parameters
    page = request.args.get('page', 1, type=int)

    # Headers
    auth = request.headers.get('Authorization')

    # Cookies
    session_id = request.cookies.get('session_id')

    # Files
    if 'file' in request.files:
        file = request.files['file']
        file.save(f"uploads/{file.filename}")

    # Request metadata
    print(request.method)      # GET, POST, etc.
    print(request.path)        # /example
    print(request.url)         # Full URL
    print(request.remote_addr) # Client IP

    return "OK"

# Response types
@app.route('/responses')
def responses():
    # String response (default 200)
    return "Hello"

    # Tuple: (body, status_code)
    return "Not Found", 404

    # Tuple: (body, status_code, headers)
    return "Created", 201, {"Location": "/resource/123"}

    # JSON response
    return jsonify({"message": "Success"})

    # Redirect
    return redirect(url_for('index'))

    # Custom response object
    response = make_response("Custom response")
    response.headers['X-Custom'] = 'Value'
    response.set_cookie('session_id', '123', max_age=3600)
    return response

    # Send file
    return send_file('report.pdf', mimetype='application/pdf')

    # Abort with error
    abort(404)
    abort(403, description="Forbidden: Admin access required")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Custom error class
class ValidationError(Exception):
    pass

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({"error": str(error)}), 400
```

---

### Templates (Jinja2)

```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/user/<username>')
def user_profile(username: str):
    user = get_user(username)
    return render_template('profile.html', user=user)

# Pass multiple variables
@app.route('/products')
def products():
    products = get_all_products()
    categories = get_categories()
    return render_template(
        'products.html',
        products=products,
        categories=categories,
        title="Product Catalog"
    )

# Using **kwargs
@app.route('/dashboard')
def dashboard():
    context = {
        "user": current_user,
        "stats": get_stats(),
        "notifications": get_notifications()
    }
    return render_template('dashboard.html', **context)
```

**templates/base.html** - Base template:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav>
        <a href="{{ url_for('index') }}">Home</a>
        <a href="{{ url_for('products') }}">Products</a>
    </nav>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>
        {% block footer %}
            &copy; 2024 Company Name
        {% endblock %}
    </footer>
</body>
</html>
```

**templates/products.html** - Child template:

```html
{% extends "base.html" %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
    <h1>Products</h1>

    {# Comments #}

    {# Conditionals #}
    {% if products %}
        <ul>
            {# Loops #}
            {% for product in products %}
                <li>
                    <h2>{{ product.name }}</h2>
                    <p>${{ product.price }}</p>

                    {# Nested conditionals #}
                    {% if product.in_stock %}
                        <span class="badge">In Stock</span>
                    {% else %}
                        <span class="badge out-of-stock">Out of Stock</span>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    {% else %}
        <p>No products found.</p>
    {% endif %}

    {# Filters #}
    <p>Total products: {{ products|length }}</p>
    <p>First product: {{ products|first }}</p>
    <p>Last product: {{ products|last }}</p>
    <p>Uppercase: {{ "hello"|upper }}</p>
    <p>Default: {{ user.nickname|default("Guest") }}</p>

    {# Custom filters (defined in app) #}
    <p>{{ price|currency }}</p>

    {# Include other templates #}
    {% include "partials/product_card.html" %}

    {# Macros (reusable components) #}
    {% macro render_product(product) %}
        <div class="product">
            <h3>{{ product.name }}</h3>
            <p>${{ product.price }}</p>
        </div>
    {% endmacro %}

    {{ render_product(products[0]) }}
{% endblock %}
```

**Custom template filters**:

```python
@app.template_filter('currency')
def currency_filter(value: float) -> str:
    return f"${value:,.2f}"

# Usage in template: {{ 1234.5|currency }} → $1,234.50
```

---

## Flask Application Structure

### Application Factory Pattern

**Recommended structure for larger applications.**

```
my_app/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # Database models
│   ├── config.py            # Configuration
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── api.py           # API routes
│   │   └── main.py          # Main routes
│   ├── templates/
│   │   ├── base.html
│   │   └── auth/
│   │       ├── login.html
│   │       └── register.html
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_api.py
├── requirements.txt
└── run.py
```

**app/__init__.py** - Application factory:

```python
from flask import Flask
from app.config import Config

def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    from app.extensions import db, login_manager
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register error handlers
    register_error_handlers(app)

    return app

def register_error_handlers(app: Flask):
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
```

**app/config.py** - Configuration:

```python
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    # Override with production values
    SECRET_KEY = os.environ['SECRET_KEY']
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

**run.py** - Entry point:

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

---

### Blueprints

**Blueprints organize routes into modules.**

**app/blueprints/auth.py**:

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import User
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('main.index'))

        flash('Invalid credentials', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
```

**app/blueprints/api.py**:

```python
from flask import Blueprint, jsonify, request
from app.models import Product
from app.extensions import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@api_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

@api_bp.route('/products', methods=['POST'])
def create_product():
    data = request.get_json()

    product = Product(
        name=data['name'],
        price=data['price'],
        description=data.get('description', '')
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(product.to_dict()), 201

@api_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    product.name = data.get('name', product.name)
    product.price = data.get('price', product.price)
    product.description = data.get('description', product.description)

    db.session.commit()

    return jsonify(product.to_dict())

@api_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    return '', 204
```

---

## Flask Advanced Patterns

### Database with SQLAlchemy

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Basic model
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Product {self.name}>'

# Relationships
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-many relationship
    orders = db.relationship('Order', backref='user', lazy='dynamic')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Many-to-many relationship
    products = db.relationship('Product', secondary='order_products', backref='orders')

# Association table for many-to-many
order_products = db.Table('order_products',
    db.Column('order_id', db.Integer, db.ForeignKey('orders.id')),
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'))
)

# Database operations
@app.route('/examples')
def database_examples():
    # Create
    product = Product(name="Laptop", price=999.99)
    db.session.add(product)
    db.session.commit()

    # Query all
    products = Product.query.all()

    # Query with filter
    expensive = Product.query.filter(Product.price > 500).all()

    # Query one
    product = Product.query.filter_by(name="Laptop").first()

    # Get by ID
    product = Product.query.get(1)
    product = Product.query.get_or_404(1)  # Auto 404 if not found

    # Update
    product = Product.query.get(1)
    product.price = 899.99
    db.session.commit()

    # Delete
    product = Product.query.get(1)
    db.session.delete(product)
    db.session.commit()

    # Complex queries
    from sqlalchemy import and_, or_

    products = Product.query.filter(
        and_(
            Product.price > 100,
            Product.price < 1000
        )
    ).order_by(Product.price.desc()).limit(10).all()

    # Relationships
    user = User.query.get(1)
    user_orders = user.orders.all()

    order = Order.query.get(1)
    order_user = order.user
    order_products = order.products

    return "OK"

# Database migrations (Flask-Migrate)
from flask_migrate import Migrate

migrate = Migrate(app, db)

# Commands:
# flask db init       # Initialize migrations
# flask db migrate -m "Create users table"  # Generate migration
# flask db upgrade    # Apply migrations
# flask db downgrade  # Rollback migrations
```

---

### Authentication with Flask-Login

```python
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user, remember=True)
        return redirect(url_for('dashboard'))

    flash('Invalid credentials')
    return redirect(url_for('login'))

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Protected route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# Custom decorator for admin
from functools import wraps

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view

@app.route('/admin')
@admin_required
def admin_panel():
    return "Admin panel"
```

---

### Testing Flask Applications

```python
import pytest
from app import create_app, db
from app.models import User, Product

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()

# Basic route test
def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Hello" in response.data

# JSON API test
def test_get_products(client):
    response = client.get('/api/products')
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)

def test_create_product(client):
    response = client.post('/api/products', json={
        'name': 'Laptop',
        'price': 999.99
    })
    assert response.status_code == 201

    data = response.get_json()
    assert data['name'] == 'Laptop'
    assert data['price'] == 999.99

# Authentication test
def test_login(client, app):
    with app.app_context():
        user = User(username='test', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

    response = client.post('/auth/login', data={
        'username': 'test',
        'password': 'password'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data

# Protected route test
def test_protected_route_requires_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302  # Redirect to login

# Database test
def test_create_user(app):
    with app.app_context():
        user = User(username='alice', email='alice@example.com')
        user.set_password('secret')
        db.session.add(user)
        db.session.commit()

        saved_user = User.query.filter_by(username='alice').first()
        assert saved_user is not None
        assert saved_user.check_password('secret')
        assert not saved_user.check_password('wrong')

# Test with fixtures
@pytest.fixture
def sample_product(app):
    with app.app_context():
        product = Product(name='Test Product', price=99.99)
        db.session.add(product)
        db.session.commit()
        return product

def test_update_product(client, sample_product):
    response = client.put(f'/api/products/{sample_product.id}', json={
        'price': 79.99
    })
    assert response.status_code == 200

    data = response.get_json()
    assert data['price'] == 79.99
```

---

## Quick Reference

### Flask Patterns

```python
# Request data
request.args.get('key')           # Query parameters (?key=value)
request.form.get('key')           # Form data (POST)
request.get_json()                # JSON body
request.files.get('file')         # Uploaded files
request.headers.get('X-Custom')   # Headers
request.cookies.get('session')    # Cookies

# Response types
return "text"                     # Plain text
return jsonify({"key": "value"})  # JSON
return render_template('page.html', var=value)  # HTML
return redirect(url_for('route')) # Redirect
return send_file('file.pdf')      # File download

# URL building
url_for('route_name')             # /path
url_for('route_name', id=123)     # /path/123
url_for('static', filename='style.css')  # /static/style.css

# Session
from flask import session
session['key'] = 'value'          # Set
value = session.get('key')        # Get
session.pop('key', None)          # Remove

# Flash messages
from flask import flash
flash('Message', 'category')
# In template: {% with messages = get_flashed_messages(with_categories=true) %}

# Abort with error
abort(404)
abort(403, description="Forbidden")

# Database operations
product = Product.query.get(id)
products = Product.query.all()
product = Product.query.filter_by(name='Laptop').first()
products = Product.query.filter(Product.price > 100).all()
db.session.add(product)
db.session.commit()
db.session.delete(product)
db.session.rollback()
```

---

### Common Flask Extensions

```python
# Flask-SQLAlchemy - Database ORM
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# Flask-Migrate - Database migrations
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Flask-Login - User authentication
from flask_login import LoginManager
login_manager = LoginManager(app)

# Flask-WTF - Forms and CSRF protection
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

# Flask-CORS - Cross-Origin Resource Sharing
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Flask-Mail - Email sending
from flask_mail import Mail, Message
mail = Mail(app)

# Flask-Caching - Caching
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.cached(timeout=60)
def expensive_operation():
    return compute_result()

# Flask-Limiter - Rate limiting
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/expensive')
@limiter.limit("5 per minute")
def expensive_endpoint():
    return "OK"
```

---

### Python CLI Cheat Sheet

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Package management
pip install flask
pip install -r requirements.txt
pip freeze > requirements.txt

# Flask commands
export FLASK_APP=app        # Linux/Mac
set FLASK_APP=app           # Windows
flask run
flask run --debug           # Debug mode
flask shell                 # Interactive shell

# Database migrations
flask db init
flask db migrate -m "message"
flask db upgrade
flask db downgrade

# Custom commands
@app.cli.command()
def seed_db():
    """Seed the database."""
    # Add seed data
    pass

# Run: flask seed_db
```

---

## Practice Exercises

1. **Create a Product API** with full CRUD endpoints (GET, POST, PUT, DELETE)
2. **Build a user authentication system** with registration, login, logout
3. **Implement a search endpoint** that filters products by name and price range
4. **Create a Blueprint** for admin routes with custom decorator for authorization
5. **Write tests** for all API endpoints using pytest
6. **Add database models** with relationships (User has many Orders, Order has many Products)
7. **Create a rate-limited endpoint** that allows 10 requests per minute
8. **Build a file upload endpoint** that validates file type and size
9. **Implement pagination** for product listing endpoint
10. **Create custom error handlers** for 400, 401, 403, 404, 500 errors

---

**Additional Resources**:
- Flask documentation: https://flask.palletsprojects.com/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/
- Pydantic documentation: https://docs.pydantic.dev/
- Python type hints: https://docs.python.org/3/library/typing.html
