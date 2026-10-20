"""SpareGo - Spare Parts Order & Delivery Management System for local auto-spare-parts shops.
Run: python app.py -> http://127.0.0.1:5000  (admin / admin123). Customers track orders at /track (no login).
"""
import random, sqlite3
from datetime import datetime
from functools import wraps
from urllib.parse import quote
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__); app.secret_key = "change-me"; DB = "sparego.db"
STATUSES = ["PLACED", "PACKED", "OUT_FOR_DELIVERY", "DELIVERED"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, shop_name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS parts(id INTEGER PRIMARY KEY, name TEXT NOT NULL, brand TEXT, vehicle TEXT NOT NULL,
  price REAL NOT NULL CHECK(price>=0), stock INTEGER NOT NULL DEFAULT 0 CHECK(stock>=0), min_stock INTEGER NOT NULL DEFAULT 3);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL, kind TEXT DEFAULT 'Individual', address TEXT);
CREATE TABLE IF NOT EXISTS riders(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), rider_id INTEGER REFERENCES riders(id),
  address TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PLACED', otp TEXT NOT NULL, delivery_fee REAL DEFAULT 0, total REAL NOT NULL,
  created_at TEXT, packed_at TEXT, out_at TEXT, delivered_at TEXT);
CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), part_id INTEGER NOT NULL REFERENCES parts(id), qty INTEGER NOT NULL, price REAL NOT NULL);
"""
def db():
    if "db" not in g: g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row; g.db.execute("PRAGMA foreign_keys=ON")
    return g.db
@app.teardown_appcontext
def _close(_):
    d = g.pop("db", None)
    if d: d.close()
def init_db():
    c = sqlite3.connect(DB); c.executescript(SCHEMA)
    if not c.execute("SELECT 1 FROM users").fetchone():
        c.execute("INSERT INTO users(username,password_hash,shop_name) VALUES(?,?,?)", ("admin", generate_password_hash("admin123"), "My Auto Spares"))
    c.commit(); c.close()
def login_required(f):
    @wraps(f)
    def w(*a, **k):
        return f(*a, **k) if "uid" in session else redirect(url_for("login"))
    return w
now = lambda: datetime.now().strftime("%Y-%m-%d %H:%M")
def fee_for(subtotal): return 0 if subtotal >= 1000 else 40      # free delivery above Rs 1000
def shop(): return db().execute("SELECT shop_name FROM users LIMIT 1").fetchone()["shop_name"]

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE username=?", (request.form["username"].strip(),)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form["password"]): session["uid"] = u["id"]; return redirect("/")
        flash("Wrong username or password", "err")
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

@app.route("/")
@login_required
def dashboard():
    d = db(); q = lambda s, a=(): d.execute(s, a).fetchone()[0]
    stats = {s: q("SELECT COUNT(*) FROM orders WHERE status=?", (s,)) for s in STATUSES}
    stats["revenue"] = q("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='DELIVERED'")
    low = d.execute("SELECT * FROM parts WHERE stock<=min_stock ORDER BY stock").fetchall()
    active = d.execute("SELECT o.*, c.name cname, r.name rname FROM orders o JOIN customers c ON c.id=o.customer_id LEFT JOIN riders r ON r.id=o.rider_id "
                       "WHERE status!='DELIVERED' ORDER BY o.id DESC LIMIT 8").fetchall()
    return render_template("dashboard.html", stats=stats, low=low, active=active, shop=shop())

@app.route("/parts", methods=["GET", "POST"])
@login_required
def parts():
    d = db()
    if request.method == "POST":
        try:
            d.execute("INSERT INTO parts(name,brand,vehicle,price,stock,min_stock) VALUES(?,?,?,?,?,?)",
                (request.form["name"].strip(), request.form["brand"].strip(), request.form["vehicle"].strip(), float(request.form["price"]),
                 int(request.form["stock"]), int(request.form["min_stock"] or 3))); d.commit(); flash("Part added", "ok")
        except (ValueError, sqlite3.IntegrityError): flash("Invalid price or stock", "err")
        return redirect("/parts")
    q = request.args.get("q", "").strip()
    rows = d.execute("SELECT * FROM parts WHERE name LIKE ? OR vehicle LIKE ? OR brand LIKE ? ORDER BY vehicle,name", (f"%{q}%",)*3).fetchall()
    return render_template("parts.html", rows=rows, q=q)

@app.route("/part/<int:pid>/restock", methods=["POST"])
@login_required
def restock(pid):
    try: n = int(request.form["qty"])
    except ValueError: n = 0
    if n > 0: db().execute("UPDATE parts SET stock=stock+? WHERE id=?", (n, pid)); db().commit(); flash("Stock updated", "ok")
    return redirect("/parts")

@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    d = db()
    if request.method == "POST":
        ph = request.form["phone"].strip()
        if not request.form["name"].strip() or not (ph.isdigit() and len(ph) == 10): flash("Name and 10-digit phone required", "err")
        else:
            d.execute("INSERT INTO customers(name,phone,kind,address) VALUES(?,?,?,?)", (request.form["name"].strip(), ph, request.form["kind"], request.form["address"].strip()))
            d.commit(); flash("Customer added", "ok")
        return redirect("/customers")
    return render_template("customers.html", rows=d.execute("SELECT c.*, (SELECT COUNT(*) FROM orders WHERE customer_id=c.id) n FROM customers c ORDER BY name").fetchall())

@app.route("/riders", methods=["GET", "POST"])
@login_required
def riders():
    d = db()
    if request.method == "POST" and request.form["name"].strip():
        d.execute("INSERT INTO riders(name,phone) VALUES(?,?)", (request.form["name"].strip(), request.form["phone"].strip())); d.commit(); flash("Rider added", "ok"); return redirect("/riders")
    return render_template("riders.html", rows=d.execute("SELECT r.*, (SELECT COUNT(*) FROM orders WHERE rider_id=r.id AND status='OUT_FOR_DELIVERY') busy, "
                           "(SELECT COUNT(*) FROM orders WHERE rider_id=r.id AND status='DELIVERED') done FROM riders r").fetchall())

@app.route("/order/new", methods=["GET", "POST"])
@login_required
def new_order():
    d = db()
    if request.method == "POST":
        ids, qtys = request.form.getlist("part_id"), request.form.getlist("qty")
        items = [(int(p), int(q)) for p, q in zip(ids, qtys) if p and q.isdigit() and int(q) > 0]
        if not request.form.get("customer_id") or not items or not request.form["address"].strip(): flash("Customer, address and at least one part required", "err"); return redirect("/order/new")
        sub, rows = 0, []
        for pid, qty in items:
            p = d.execute("SELECT * FROM parts WHERE id=?", (pid,)).fetchone()
            if qty > p["stock"]: flash(f"{p['name']}: only {p['stock']} in stock", "err"); return redirect("/order/new")
            sub += p["price"] * qty; rows.append((pid, qty, p["price"]))
        fee = fee_for(sub)
        cur = d.execute("INSERT INTO orders(customer_id,address,otp,delivery_fee,total,created_at) VALUES(?,?,?,?,?,?)",
                        (request.form["customer_id"], request.form["address"].strip(), str(random.randint(1000, 9999)), fee, sub + fee, now()))
        for pid, qty, price in rows:
            d.execute("INSERT INTO order_items(order_id,part_id,qty,price) VALUES(?,?,?,?)", (cur.lastrowid, pid, qty, price))
            d.execute("UPDATE parts SET stock=stock-? WHERE id=?", (qty, pid))
        d.commit(); flash(f"Order #{cur.lastrowid} placed. Total Rs {sub+fee:.0f}", "ok"); return redirect(f"/order/{cur.lastrowid}")
    return render_template("new_order.html", parts=d.execute("SELECT * FROM parts WHERE stock>0 ORDER BY vehicle,name").fetchall(),
                           customers=d.execute("SELECT * FROM customers ORDER BY name").fetchall())

@app.route("/orders")
@login_required
def orders():
    s = request.args.get("status", "")
    sql = "SELECT o.*, c.name cname, r.name rname FROM orders o JOIN customers c ON c.id=o.customer_id LEFT JOIN riders r ON r.id=o.rider_id"
    rows = db().execute(sql + (" WHERE status=?" if s else "") + " ORDER BY o.id DESC", (s,) if s else ()).fetchall()
    return render_template("orders.html", rows=rows, s=s, statuses=STATUSES)

@app.route("/order/<int:oid>")
@login_required
def order_detail(oid):
    d = db()
    o = d.execute("SELECT o.*, c.name cname, c.phone cphone, r.name rname FROM orders o JOIN customers c ON c.id=o.customer_id LEFT JOIN riders r ON r.id=o.rider_id WHERE o.id=?", (oid,)).fetchone()
    if not o: return redirect("/orders")
    items = d.execute("SELECT i.*, p.name pname FROM order_items i JOIN parts p ON p.id=i.part_id WHERE order_id=?", (oid,)).fetchall()
    link = request.host_url.rstrip("/") + url_for("track", oid=oid)
    msg = f"Namaste {o['cname']}, aapka order #{oid} ({shop()}) confirm hai. Track karein: {link} . Delivery OTP: {o['otp']}"
    wa = f"https://wa.me/91{o['cphone']}?text={quote(msg)}"
    return render_template("order_detail.html", o=o, items=items, riders=d.execute("SELECT * FROM riders WHERE active=1").fetchall(), wa=wa, shop=shop(), link=link)

@app.route("/order/<int:oid>/advance", methods=["POST"])
@login_required
def advance(oid):
    d = db(); o = d.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if o["status"] == "PLACED":
        d.execute("UPDATE orders SET status='PACKED', packed_at=? WHERE id=?", (now(), oid)); flash("Order packed", "ok")
    elif o["status"] == "PACKED":
        if not request.form.get("rider_id"): flash("Assign a rider first", "err"); return redirect(f"/order/{oid}")
        d.execute("UPDATE orders SET status='OUT_FOR_DELIVERY', rider_id=?, out_at=? WHERE id=?", (request.form["rider_id"], now(), oid)); flash("Out for delivery", "ok")
    elif o["status"] == "OUT_FOR_DELIVERY":
        if request.form.get("otp", "").strip() != o["otp"]: flash("Wrong delivery OTP - not delivered", "err"); return redirect(f"/order/{oid}")
        d.execute("UPDATE orders SET status='DELIVERED', delivered_at=? WHERE id=?", (now(), oid)); flash("Delivered", "ok")
    d.commit(); return redirect(f"/order/{oid}")

@app.route("/track", methods=["GET", "POST"])
@app.route("/track/<int:oid>")
def track(oid=None):
    """Public order tracking - no login needed."""
    if request.method == "POST":
        ph, oid = request.form["phone"].strip(), request.form["oid"].strip()
        row = db().execute("SELECT o.id FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id=? AND c.phone=?", (oid, ph)).fetchone()
        if row: return redirect(url_for("track", oid=row["id"]))
        flash("Order not found for this phone number", "err"); return redirect("/track")
    o = db().execute("SELECT o.*, r.name rname, r.phone rphone FROM orders o LEFT JOIN riders r ON r.id=o.rider_id WHERE o.id=?", (oid,)).fetchone() if oid else None
    return render_template("track.html", o=o, statuses=STATUSES)

@app.route("/reports")
@login_required
def reports():
    d = db()
    top = d.execute("SELECT p.name, p.vehicle, SUM(i.qty) q FROM order_items i JOIN parts p ON p.id=i.part_id GROUP BY p.id ORDER BY q DESC LIMIT 5").fetchall()
    perf = d.execute("SELECT r.name, COUNT(o.id) n, AVG((julianday(o.delivered_at)-julianday(o.out_at))*1440) mins FROM riders r LEFT JOIN orders o ON o.rider_id=r.id AND o.status='DELIVERED' GROUP BY r.id").fetchall()
    daily = d.execute("SELECT substr(created_at,1,10) dt, SUM(total) t FROM orders GROUP BY dt ORDER BY dt DESC LIMIT 7").fetchall()[::-1]
    return render_template("reports.html", top=top, perf=perf, daily=daily, mx=max([r["t"] for r in daily] or [1]))

if __name__ == "__main__": init_db(); app.run(debug=True)
