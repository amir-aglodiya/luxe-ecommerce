import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config


def get_db():
    if "db" not in g:
        database = current_app.config["DATABASE"]
        Path(os.path.dirname(database)).mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_schema(db):
    existing_columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    for column in ("phone", "address", "role"):
        if column not in existing_columns:
            default = "'CUSTOMER'" if column == "role" else "''"
            db.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT NOT NULL DEFAULT {default}")
    db.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "ADMIN":
            flash("Admin access is required.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.executescript((Path(app.root_path) / "schema.sql").read_text())
        ensure_schema(db)

    @app.context_processor
    def inject_cart_count():
        cart = session.get("cart", {})
        return {"cart_count": sum(cart.values())}

    @app.get("/")
    def index():
        products = get_db().execute(
            "SELECT * FROM products ORDER BY featured DESC, id DESC LIMIT 4"
        ).fetchall()
        return render_template("index.html", products=products)

    @app.get("/support")
    def support():
        return render_template("support.html")

    @app.get("/shop")
    def shop():
        category = request.args.get("category", "")
        query = "SELECT * FROM products"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY featured DESC, name"
        products = get_db().execute(query, params).fetchall()
        categories = get_db().execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
        return render_template("shop.html", products=products, categories=categories, active_category=category)

    @app.get("/product/<int:product_id>")
    def product(product_id):
        item = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if item is None:
            abort(404)
        return render_template("product.html", product=item)

    @app.post("/cart/add/<int:product_id>")
    def add_to_cart(product_id):
        item = get_db().execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if item is None:
            abort(404)
        cart = session.setdefault("cart", {})
        key = str(product_id)
        cart[key] = cart.get(key, 0) + max(1, int(request.form.get("quantity", 1)))
        session.modified = True
        flash("Added to your bag.", "success")
        return redirect(request.form.get("next") or url_for("shop"))

    @app.get("/cart")
    def cart():
        cart = session.get("cart", {})
        items = []
        total = 0
        for product_id, quantity in cart.items():
            item = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if item:
                line_total = item["price"] * quantity
                total += line_total
                items.append({"product": item, "quantity": quantity, "line_total": line_total})
        return render_template("cart.html", items=items, total=total)

    @app.post("/cart/remove/<int:product_id>")
    def remove_from_cart(product_id):
        session.get("cart", {}).pop(str(product_id), None)
        session.modified = True
        return redirect(url_for("cart"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = get_db().execute("SELECT * FROM users WHERE email = ?", (request.form["email"].lower().strip(),)).fetchone()
            if user and check_password_hash(user["password"], request.form["password"]):
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["role"] = user["role"]
                return redirect(request.args.get("next") or url_for("index"))
            flash("Email or password is incorrect.", "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name, email, password = request.form["name"].strip(), request.form["email"].lower().strip(), request.form["password"]
            if not name or len(password) < 6:
                flash("Use a name and a password of at least 6 characters.", "error")
            else:
                try:
                    db = get_db()
                    db.execute(
                        "INSERT INTO users (name, email, password, phone, address, role) VALUES (?, ?, ?, ?, ?, 'CUSTOMER')",
                        (name, email, generate_password_hash(password), request.form.get("phone", "").strip(), request.form.get("address", "").strip()),
                    )
                    db.commit()
                    flash("Account created. You can now sign in.", "success")
                    return redirect(url_for("login"))
                except sqlite3.IntegrityError:
                    flash("That email is already registered.", "error")
        return render_template("register.html")

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            identity = request.form["identity"].strip().lower()
            admin = get_db().execute(
                "SELECT * FROM users WHERE (email = ? OR name = ?) AND role = 'ADMIN'",
                (identity, identity),
            ).fetchone()
            if admin and check_password_hash(admin["password"], request.form["password"]):
                session.clear()
                session["user_id"] = admin["id"]
                session["user_name"] = admin["name"]
                session["role"] = "ADMIN"
                return redirect(url_for("admin_dashboard"))
            flash("Admin credentials are incorrect.", "error")
        return render_template("admin_login.html")

    @app.get("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("admin_login"))

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        db = get_db()
        stats = {
            "products": db.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "customers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'CUSTOMER'").fetchone()[0],
            "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "revenue": db.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE status != 'Cancelled'").fetchone()[0],
            "pending": db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Pending', 'Processing')").fetchone()[0],
        }
        recent_orders = db.execute("""
            SELECT orders.id, users.name AS customer, orders.total, orders.status, orders.created_at
            FROM orders JOIN users ON users.id = orders.user_id ORDER BY orders.id DESC LIMIT 8
        """).fetchall()
        return render_template("admin_dashboard.html", stats=stats, recent_orders=recent_orders)

    @app.route("/admin/products", methods=["GET", "POST"])
    @admin_required
    def admin_products():
        db = get_db()
        if request.method == "POST":
            name = request.form["name"].strip()
            price = float(request.form["price"])
            if name and price >= 0:
                db.execute(
                    "INSERT INTO products (name, category, description, price, image, featured) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, request.form.get("category", "Uncategorized"), request.form.get("description", ""), price, request.form.get("image", ""), int(request.form.get("featured", 0))),
                )
                db.commit()
                flash("Product added.", "success")
                return redirect(url_for("admin_products"))
            flash("Product name and a valid price are required.", "error")
        products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        return render_template("admin_products.html", products=products)

    @app.post("/admin/products/<int:product_id>/delete")
    @admin_required
    def admin_delete_product(product_id):
        db = get_db()
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
        flash("Product removed.", "success")
        return redirect(url_for("admin_products"))

    @app.get("/admin/orders")
    @admin_required
    def admin_orders():
        orders = get_db().execute("""
            SELECT orders.id, users.name AS customer, users.email, orders.total, orders.status, orders.created_at
            FROM orders JOIN users ON users.id = orders.user_id ORDER BY orders.id DESC
        """).fetchall()
        return render_template("admin_orders.html", orders=orders)

    @app.post("/admin/orders/<int:order_id>/status")
    @admin_required
    def admin_order_status(order_id):
        allowed = {"Pending", "Confirmed", "Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled"}
        status = request.form.get("status")
        if status in allowed:
            db = get_db()
            db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            db.commit()
            flash("Order status updated.", "success")
        return redirect(url_for("admin_orders"))

    @app.get("/orders")
    @login_required
    def orders():
        rows = get_db().execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)).fetchall()
        details = get_db().execute("SELECT * FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?) ORDER BY order_id DESC, id", (session["user_id"],)).fetchall()
        return render_template("orders.html", orders=rows, order_items=details)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        db = get_db()
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].lower().strip()
            if not name or not email:
                flash("Name and email are required.", "error")
            else:
                try:
                    db.execute(
                        "UPDATE users SET name = ?, email = ?, phone = ?, address = ? WHERE id = ?",
                        (name, email, request.form.get("phone", "").strip(), request.form.get("address", "").strip(), session["user_id"]),
                    )
                    db.commit()
                    session["user_name"] = name
                    flash("Your profile was updated.", "success")
                except sqlite3.IntegrityError:
                    flash("That email is already registered.", "error")
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        return render_template("profile.html", user=user)

    @app.get("/database")
    @admin_required
    def database_view():
        db = get_db()
        users = db.execute("SELECT id, name, email, phone, address, created_at FROM users ORDER BY id DESC").fetchall()
        products = db.execute("SELECT id, name, category, price, featured FROM products ORDER BY id DESC").fetchall()
        orders = db.execute("""
            SELECT orders.id, users.name AS customer, orders.total, orders.status, orders.created_at
            FROM orders JOIN users ON users.id = orders.user_id ORDER BY orders.id DESC
        """).fetchall()
        order_items = db.execute("SELECT order_id, product_name, unit_price, quantity FROM order_items ORDER BY order_id DESC, id").fetchall()
        return render_template("database.html", users=users, products=products, orders=orders, order_items=order_items)

    @app.post("/checkout")
    @login_required
    def checkout():
        cart = session.get("cart", {})
        if not cart:
            flash("Your bag is empty.", "error")
            return redirect(url_for("cart"))
        db = get_db()
        purchased_items = []
        total = 0
        for product_id, quantity in cart.items():
            row = db.execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,)).fetchone()
            if row:
                total += row["price"] * quantity
                purchased_items.append((row, quantity))
        cursor = db.execute("INSERT INTO orders (user_id, total, status) VALUES (?, ?, ?)", (session["user_id"], total, "Confirmed"))
        db.executemany(
            "INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity) VALUES (?, ?, ?, ?, ?)",
            [(cursor.lastrowid, item["id"], item["name"], item["price"], quantity) for item, quantity in purchased_items],
        )
        db.commit()
        session["cart"] = {}
        flash("Order placed. Thank you for shopping with Luxe.", "success")
        return redirect(url_for("index"))

    return app
