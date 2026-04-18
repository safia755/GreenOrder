from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import time
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev_key_change_me")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SESSION_TIMEOUT = 1800

# ================= INIT DB =================
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        created_at TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        restaurant_id INTEGER,
        created_at TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        category TEXT,
        description TEXT,
        image TEXT,
        options TEXT,
        restaurant_id INTEGER,
        created_at TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_number INTEGER,
        items TEXT,
        status TEXT,
        created_at TEXT,
        restaurant_id INTEGER
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        table_number INTEGER
    )""")

    conn.commit()
    conn.close()

init_db()

# ================= SESSION =================
@app.before_request
def check_session():
    if "restaurant_id" in session:
        last = session.get("last_activity", time.time())
        if time.time() - last > SESSION_TIMEOUT:
            session.clear()
            return redirect("/login")
        session["last_activity"] = time.time()

# ================= AUTH =================
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    try:
        c.execute("""
        INSERT INTO restaurants (name, phone, password, created_at)
        VALUES (?, ?, ?, ?)
        """, (
            data.get("restaurant"),
            data.get("phone"),
            generate_password_hash(data.get("password")),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return jsonify({"message": "Restaurant créé"})
    except:
        return jsonify({"message": "Numéro déjà utilisé"}), 400
    finally:
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM restaurants WHERE phone=?", (data.get("phone"),))
    user = c.fetchone()
    conn.close()

    if not user:
        return jsonify({"message": "Numéro introuvable"}), 401

    if not check_password_hash(user[3], data.get("password")):
        return jsonify({"message": "Mot de passe incorrect"}), 401

    session["restaurant_id"] = user[0]
    session["last_activity"] = time.time()

    return jsonify({"message": "Connexion réussie"})

# ================= PAGES =================
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/landing")
def landing_page():
    return render_template("landing.html")

@app.route("/admin")
def admin():
    if "restaurant_id" not in session:
        return redirect("/login")
    return render_template("admin.html")

@app.route("/kitchen")
def kitchen():
    if "restaurant_id" not in session:
        return redirect("/login")
    return render_template("kitchen.html")

@app.route("/menu")
def menu():
    return render_template("menu.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# ================= CATEGORIES =================
@app.route("/api/categories")
def categories():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE restaurant_id=?", (session.get("restaurant_id"),))
    data = c.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/api/add_category", methods=["POST"])
def add_category():
    data = request.get_json()
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO categories (name, restaurant_id, created_at)
    VALUES (?, ?, ?)
    """, (
        data.get("name"),
        session.get("restaurant_id"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()
    return jsonify({"message": "Catégorie ajoutée"})

@app.route("/api/delete_category/<int:id>", methods=["DELETE"])
def delete_category(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # récupérer le nom de la catégorie
    c.execute("""
        SELECT name FROM categories
        WHERE id=? AND restaurant_id=?
    """, (id, session.get("restaurant_id")))
    
    cat = c.fetchone()

    if not cat:
        conn.close()
        return jsonify({"message": "Catégorie introuvable"}), 404

    category_name = cat[0]

    # supprimer les produits liés à cette catégorie
    c.execute("""
        DELETE FROM products
        WHERE category=? AND restaurant_id=?
    """, (category_name, session.get("restaurant_id")))

    # supprimer la catégorie
    c.execute("""
    DELETE FROM categories
    WHERE id=? AND restaurant_id=?
""", (id, session.get("restaurant_id")))

    conn.commit()
    conn.close()

    return jsonify({"message": "Catégorie supprimée"})

# ================= PRODUCTS =================
@app.route("/api/products")
def products():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE restaurant_id=?", (session.get("restaurant_id"),))
    rows = c.fetchall()
    conn.close()

    result = []

    for r in rows:
        try:
            options = json.loads(r[6]) if r[6] else []
        except:
            options = []

        result.append({
            "id": r[0],
            "name": r[1],
            "price": r[2],
            "category": r[3],
            "description": r[4],
            "image": r[5],
            "options": options
        })

    return jsonify(result)

@app.route("/api/add_product", methods=["POST"])
def add_product():
    data = request.get_json()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO products
        (name, price, category, description, image, options, restaurant_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        float(data.get("price", 0)),
        data.get("category"),
        data.get("description"),
        data.get("image"),
        "[]",
        session.get("restaurant_id"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Produit ajouté"})

@app.route("/api/delete_product/<int:id>", methods=["DELETE"])
def delete_product(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        DELETE FROM products
        WHERE id=? AND restaurant_id=?
    """, (id, session.get("restaurant_id")))

    conn.commit()
    conn.close()
    return jsonify({"message": "deleted"})

@app.route("/api/edit_product/<int:id>", methods=["PUT"])
def edit_product(id):
    data = request.get_json()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        UPDATE products
        SET name=?, price=?, category=?, description=?, image=?
        WHERE id=? AND restaurant_id=?
    """, (
        data.get("name"),
        data.get("price"),
        data.get("category"),
        data.get("description"),
        data.get("image"),
        id,
        session.get("restaurant_id")
    ))

    conn.commit()
    conn.close()
    return jsonify({"message": "updated"})

# ================= ORDERS =================
@app.route("/api/add_order", methods=["POST"])
def add_order():
    data = request.get_json()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO orders (table_number, items, status, created_at, restaurant_id)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("table"),
        json.dumps(data.get("items")),
        "En attente",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        session.get("restaurant_id")
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Commande envoyée"})

@app.route("/api/orders")
def get_orders():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM orders WHERE restaurant_id=? AND status!='Prêt'",
              (session.get("restaurant_id"),))
    rows = c.fetchall()
    conn.close()

    result = []

    for r in rows:
        try:
            items = json.loads(r[2])
        except:
            items = []

        total = 0
        for it in items:
            total += (float(it.get("price", 0)) + float(it.get("optionPrice", 0))) * int(it.get("qty", 1))

        result.append({
            "id": r[0],
            "table": r[1],
            "items": items,
            "status": r[3],
            "time": r[4],
            "total": total
        })

    return jsonify(result)

@app.route("/api/orders_history")
def history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, table_number, items, status, created_at
        FROM orders
        WHERE restaurant_id=?
        ORDER BY id DESC
    """, (session.get("restaurant_id"),))

    rows = c.fetchall()
    conn.close()

    result = []

    for r in rows:
        try:
            items = json.loads(r[2])
        except:
            items = []

        total = 0
        formatted_items = []

        for it in items:
            name = it.get("name", "Produit")
            price = float(it.get("price", 0))
            qty = int(it.get("qty", 1))

            subtotal = price * qty
            total += subtotal

            formatted_items.append({
                "name": name,
                "qty": qty,
                "price": price,
                "subtotal": subtotal
            })

        result.append({
            "id": r[0],
            "table": r[1],
            "items": formatted_items,
            "status": r[3],
            "time": r[4],
            "total": round(total, 2)
        })

    return jsonify(result)

@app.route("/api/order_ready/<int:id>", methods=["POST"])
def order_ready(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status='Prêt' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Prêt"})

# ================= DASHBOARD =================
@app.route("/api/dashboard_stats")
def dashboard_stats():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    rid = session.get("restaurant_id")

    from datetime import datetime, timedelta

    # ================= BASE STATS =================
    c.execute("SELECT COUNT(*) FROM products WHERE restaurant_id=?", (rid,))
    products = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id=?", (rid,))
    categories = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE restaurant_id=?", (rid,))
    total_orders = c.fetchone()[0]

    # ================= TODAY REVENUE =================
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("""
        SELECT items FROM orders
        WHERE restaurant_id=? AND created_at LIKE ?
    """, (rid, today + "%"))

    rows = c.fetchall()

    revenue_today = 0
    product_count = {}

    for r in rows:
        try:
            items = json.loads(r[0])
        except:
            items = []

        for it in items:
            name = it.get("name", "Unknown")
            qty = int(it.get("qty", 1))
            price = float(it.get("price", 0))

            revenue_today += price * qty

            product_count[name] = product_count.get(name, 0) + qty

    # ================= MONTH REVENUE =================
    month = datetime.now().strftime("%Y-%m")

    c.execute("""
        SELECT items FROM orders
        WHERE restaurant_id=? AND created_at LIKE ?
    """, (rid, month + "%"))

    rows = c.fetchall()

    revenue_month = 0

    for r in rows:
        try:
            items = json.loads(r[0])
        except:
            items = []

        for it in items:
            qty = int(it.get("qty", 1))
            price = float(it.get("price", 0))
            revenue_month += price * qty

    # ================= TOP PRODUCTS =================
    top_products = sorted(
        product_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    conn.close()

    return jsonify({
        "products": products,
        "categories": categories,
        "total_orders": total_orders,
        "revenue_today": round(revenue_today, 2),
        "revenue_month": round(revenue_month, 2),
        "top_products": top_products
    })



  

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/api/upload_image", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    filename = secure_filename(file.filename)

    # rendre unique
    unique_name = str(int(time.time())) + "_" + filename

    path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(path)

    return jsonify({
        "url": "/static/uploads/" + unique_name
    })
@app.route("/api/generate_qr_tables")
def generate_qr_tables():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    rid = session.get("restaurant_id")

    c.execute("SELECT restaurant_id, table_number FROM tables WHERE restaurant_id=?", (rid,))
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {"restaurant_id": r[0], "table_number": r[1]}
        for r in rows
    ])
    
@app.route("/api/add_tables", methods=["POST"])
def add_tables():
    data = request.get_json()
    rid = session.get("restaurant_id")

    nb = int(data.get("number"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT MAX(table_number) FROM tables WHERE restaurant_id=?", (rid,))
    last = c.fetchone()[0] or 0

    for i in range(1, nb + 1):
        c.execute("""
            INSERT INTO tables (restaurant_id, table_number)
            VALUES (?, ?)
        """, (rid, last + i))

    conn.commit()
    conn.close()

    return jsonify({"message": "ok"})
# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)