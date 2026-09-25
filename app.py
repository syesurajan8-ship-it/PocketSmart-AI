import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from google import genai
except ImportError:
    genai = None

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")
app.config["JSON_SORT_KEYS"] = False

DB_PATH = BASE_DIR / "data" / "pocketsmart.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

MODEL_CANDIDATES = [
    os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            planner_type TEXT NOT NULL,
            title TEXT NOT NULL,
            budget REAL NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = db()
    user = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return dict(user) if user else None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def demo_recommendation(planner, payload):
    budget = float(payload.get("budget") or 0)
    location = payload.get("location") or "your area"
    style = payload.get("style") or "balanced"
    party_size = payload.get("party_size") or "not specified"

    if planner == "home":
        return {
            "summary": f"A practical {style} home plan for {location} within ₹{budget:,.0f}.",
            "items": [
                {"name": "Lighting refresh", "reason": "High visual impact without replacing major furniture.", "estimate": max(2500, budget * 0.12)},
                {"name": "Textiles & decor", "reason": "Adds warmth and can be changed later.", "estimate": max(3000, budget * 0.18)},
                {"name": "Storage upgrade", "reason": "Improves everyday function and keeps the room organized.", "estimate": max(4000, budget * 0.25)},
                {"name": "Accent furniture", "reason": "Use the remaining budget on one statement piece.", "estimate": max(5000, budget * 0.35)},
            ],
            "tip": "Keep 10% as a contingency so the plan remains comfortable if prices change."
        }
    if planner == "party":
        return {
            "summary": f"A {style} party plan for about {party_size} guests in {location}, targeting ₹{budget:,.0f}.",
            "items": [
                {"name": "Food & drinks", "reason": "Prioritize the guest experience and reliable quantities.", "estimate": max(5000, budget * 0.45)},
                {"name": "Decor", "reason": "Concentrate decoration on one photo-friendly area.", "estimate": max(2000, budget * 0.18)},
                {"name": "Venue & seating", "reason": "Keep the layout comfortable and easy to clean.", "estimate": max(3000, budget * 0.22)},
                {"name": "Contingency", "reason": "Protect the budget from last-minute purchases.", "estimate": max(1000, budget * 0.10)},
            ],
            "tip": "Reserve a small buffer instead of spending the entire budget upfront."
        }
    return {
        "summary": f"A {style} jewellery buying plan for {location} within ₹{budget:,.0f}.",
        "items": [
            {"name": "Core piece", "reason": "Put most of the budget into the piece you will wear most.", "estimate": max(6000, budget * 0.60)},
            {"name": "Matching accent", "reason": "Choose a simpler complementary item.", "estimate": max(2000, budget * 0.18)},
            {"name": "Care & storage", "reason": "Protect the purchase with basic storage and cleaning.", "estimate": max(500, budget * 0.07)},
            {"name": "Price buffer", "reason": "Leave room for taxes, making charges, or price changes.", "estimate": max(500, budget * 0.10)},
        ],
        "tip": "Compare total cost, not only the displayed item price, before buying."
    }

def gemini_recommendation(planner, payload):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return demo_recommendation(planner, payload) | {"mode": "demo", "note": "Add GEMINI_API_KEY to .env to enable Gemini recommendations."}

    client = genai.Client(api_key=api_key)
    prompt = f"""
You are PocketSmart, a careful personal budgeting assistant.
Create a useful budget plan for the user's request.

Planner: {planner}
User details: {payload}

Rules:
- Currency is INR (₹) unless the user explicitly says otherwise.
- Never claim a live price or availability unless the user supplied it.
- Give practical ranges and explain assumptions.
- Do not encourage debt or risky financial behavior.
- Return ONLY valid JSON with this shape:
{{
  "summary": "one short paragraph",
  "items": [
    {{"name": "item", "reason": "why", "estimate": 0}}
  ],
  "tip": "one practical tip"
}}
Use 4 to 6 items and keep the total of estimates at or below the stated budget when a budget is provided.
"""
    last_error = None
    for model in dict.fromkeys(MODEL_CANDIDATES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.4},
            )
            text = response.text or ""
            data = json.loads(text)
            data["mode"] = "gemini"
            data["model"] = model
            return data
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            # A model-not-found response should move to the next known model.
            if "404" in message or "not found" in message or "not_found" in message:
                continue
            break

    fallback = demo_recommendation(planner, payload)
    fallback["mode"] = "fallback"
    fallback["note"] = "Gemini could not be reached. The app returned a local safe fallback so the page still works."
    if os.getenv("DEBUG_GEMINI") == "1":
        fallback["debug"] = str(last_error)
    return fallback

@app.get("/")
def home():
    return render_template("index.html", user=current_user())

@app.get("/login")
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="login", user=None)

@app.get("/signup")
def signup():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="signup", user=None)

@app.post("/api/signup")
def api_signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3 or len(email) < 5 or len(password) < 6:
        return jsonify(error="Use a username of 3+ characters, a valid email, and a password of 6+ characters."), 400

    conn = db()
    try:
        cur = conn.execute(
            "INSERT INTO users(username,email,password_hash,created_at) VALUES (?,?,?,?)",
            (username, email, generate_password_hash(password), datetime.utcnow().isoformat()),
        )
        conn.commit()
        session["user_id"] = cur.lastrowid
        return jsonify(ok=True, redirect="/dashboard")
    except sqlite3.IntegrityError:
        return jsonify(error="That username or email is already registered."), 409
    finally:
        conn.close()

@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    identity = (data.get("identity") or "").strip().lower()
    password = data.get("password") or ""

    conn = db()
    user = conn.execute(
        "SELECT * FROM users WHERE lower(username)=? OR lower(email)=?",
        (identity, identity),
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Incorrect username/email or password."), 401

    session["user_id"] = user["id"]
    return jsonify(ok=True, redirect="/dashboard")

@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(ok=True, redirect="/")

@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user())

@app.get("/planner/<planner>")
def planner(planner):
    if planner not in {"home", "party", "jewelry"}:
        return render_template("404.html"), 404
    names = {"home": "Home Interior", "party": "Party", "jewelry": "Jewellery"}
    return render_template("planner.html", planner=planner, planner_name=names[planner], user=current_user())

@app.post("/api/recommend")
def api_recommend():
    data = request.get_json(silent=True) or {}
    planner = data.get("planner", "home")
    if planner not in {"home", "party", "jewelry"}:
        return jsonify(error="Unknown planner."), 400

    result = gemini_recommendation(planner, data)

    if current_user():
        conn = db()
        conn.execute(
            "INSERT INTO plans(user_id, planner_type, title, budget, details, created_at) VALUES (?,?,?,?,?,?)",
            (current_user()["id"], planner, result.get("summary", "PocketSmart plan"), float(data.get("budget") or 0), json.dumps(result), datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

    return jsonify(result)

@app.get("/api/plans")
@login_required
def api_plans():
    conn = db()
    rows = conn.execute(
        "SELECT id, planner_type, title, budget, details, created_at FROM plans WHERE user_id=? ORDER BY id DESC",
        (current_user()["id"],)
    ).fetchall()
    conn.close()
    plans = []
    for row in rows:
        plans.append({
            "id": row["id"],
            "planner_type": row["planner_type"],
            "title": row["title"],
            "budget": row["budget"],
            "details": json.loads(row["details"]),
            "created_at": row["created_at"],
        })
    return jsonify(plans)

@app.get("/api/health")
def api_health():
    return jsonify(ok=True, app="PocketSmart AI", gemini_configured=bool(os.getenv("GEMINI_API_KEY")))

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "1") == "1")
