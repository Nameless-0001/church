from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
import os
import csv
import io
from datetime import datetime
from functools import wraps
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
CORS(app)

DB_FILE = os.environ.get("DB_FILE", "church.db")


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS churches (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                slug      TEXT    UNIQUE NOT NULL,
                name      TEXT    NOT NULL,
                password  TEXT    NOT NULL,
                created_at TEXT   NOT NULL
            );

            CREATE TABLE IF NOT EXISTS visitors (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                church_id  INTEGER NOT NULL,
                date       TEXT NOT NULL,
                time       TEXT NOT NULL,
                name       TEXT NOT NULL,
                phone      TEXT NOT NULL,
                email      TEXT,
                visit_type TEXT NOT NULL,
                FOREIGN KEY (church_id) REFERENCES churches(id)
            );
        """)
        # Seed a demo church if none exist
        existing = conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0]
        if existing == 0:
            conn.execute(
                "INSERT INTO churches (slug, name, password, created_at) VALUES (?, ?, ?, ?)",
                ("kingdom-ways", "Kingdom Ways", _hash("admin123"), datetime.now().isoformat())
            )
            print("✓ Demo church created: slug=kingdom-ways  password=admin123")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        slug = kwargs.get("slug")
        if not session.get(f"admin_{slug}"):
            return redirect(url_for("admin_login", slug=slug))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Visitor form  (public)
# ---------------------------------------------------------------------------

@app.route("/<slug>")
def visitor_form(slug):
    with get_db() as conn:
        church = conn.execute("SELECT * FROM churches WHERE slug=?", (slug,)).fetchone()
    if not church:
        return "Church not found", 404
    return render_template("form.html", church=church)


@app.route("/<slug>/register", methods=["POST"])
def register(slug):
    with get_db() as conn:
        church = conn.execute("SELECT * FROM churches WHERE slug=?", (slug,)).fetchone()
        if not church:
            return jsonify({"error": "Church not found"}), 404

        data       = request.json or {}
        name       = data.get("name", "").strip()
        phone      = data.get("phone", "").strip()
        email      = data.get("email", "").strip()
        visit_type = data.get("visit_type", "").strip()

        if not name or not phone or not visit_type:
            return jsonify({"error": "Missing required fields"}), 400

        now = datetime.now()
        conn.execute(
            "INSERT INTO visitors (church_id, date, time, name, phone, email, visit_type) VALUES (?,?,?,?,?,?,?)",
            (church["id"], now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
             name, phone, email, visit_type)
        )
        print(f"✓ [{church['name']}] Visitor saved: {name} ({visit_type})")
    return jsonify({"message": "Saved successfully"})


# ---------------------------------------------------------------------------
# Admin — login
# ---------------------------------------------------------------------------

@app.route("/<slug>/admin/login", methods=["GET", "POST"])
def admin_login(slug):
    with get_db() as conn:
        church = conn.execute("SELECT * FROM churches WHERE slug=?", (slug,)).fetchone()
    if not church:
        return "Church not found", 404

    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if _hash(pw) == church["password"]:
            session[f"admin_{slug}"] = True
            return redirect(url_for("admin_dashboard", slug=slug))
        error = "Incorrect password"

    return render_template("login.html", church=church, error=error)


@app.route("/<slug>/admin/logout")
def admin_logout(slug):
    session.pop(f"admin_{slug}", None)
    return redirect(url_for("admin_login", slug=slug))


# ---------------------------------------------------------------------------
# Admin — dashboard
# ---------------------------------------------------------------------------

@app.route("/<slug>/admin")
@login_required
def admin_dashboard(slug):
    with get_db() as conn:
        church   = conn.execute("SELECT * FROM churches WHERE slug=?", (slug,)).fetchone()
        visitors = conn.execute(
            "SELECT * FROM visitors WHERE church_id=? ORDER BY date DESC, time DESC",
            (church["id"],)
        ).fetchall()
        total      = len(visitors)
        first_time = sum(1 for v in visitors if v["visit_type"] == "First time visitor")
        members    = sum(1 for v in visitors if v["visit_type"] == "Regular member")
        returning  = sum(1 for v in visitors if v["visit_type"] == "Returning visitor")

    return render_template("admin.html", church=church, visitors=visitors,
                           total=total, first_time=first_time,
                           members=members, returning=returning)


# ---------------------------------------------------------------------------
# Admin — export CSV
# ---------------------------------------------------------------------------

@app.route("/<slug>/admin/export")
@login_required
def export_csv(slug):
    with get_db() as conn:
        church   = conn.execute("SELECT * FROM churches WHERE slug=?", (slug,)).fetchone()
        visitors = conn.execute(
            "SELECT date, time, name, phone, email, visit_type FROM visitors WHERE church_id=? ORDER BY date DESC, time DESC",
            (church["id"],)
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Time", "Name", "Phone", "Email", "Visit Type"])
    for v in visitors:
        writer.writerow(list(v))

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{slug}-visitors.csv"
    )


# ---------------------------------------------------------------------------
# Super-admin: create a new church account
# ---------------------------------------------------------------------------

@app.route("/setup/new-church", methods=["GET", "POST"])
def new_church():
    """Simple setup page to onboard a new church."""
    setup_key = os.environ.get("SETUP_KEY", "changeme")
    error = None
    success = None

    if request.method == "POST":
        if request.form.get("setup_key") != setup_key:
            error = "Invalid setup key"
        else:
            name     = request.form.get("name", "").strip()
            slug     = request.form.get("slug", "").strip().lower().replace(" ", "-")
            password = request.form.get("password", "").strip()
            if not name or not slug or not password:
                error = "All fields are required"
            else:
                try:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO churches (slug, name, password, created_at) VALUES (?,?,?,?)",
                            (slug, name, _hash(password), datetime.now().isoformat())
                        )
                    success = f"Church created! Visitor form: /{slug}  |  Admin: /{slug}/admin"
                except sqlite3.IntegrityError:
                    error = f"Slug '{slug}' already taken"

    return render_template("new_church.html", error=error, success=success)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
