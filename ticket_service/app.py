from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import time
import hmac
import hashlib
import base64
import bcrypt

app = Flask(__name__)
CORS(app)

db_path = "/data/tickets.db"
SECRET = os.environ.get("AUTH_SECRET", "changeme-secret")
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

os.makedirs("/data", exist_ok=True)
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, user_id TEXT, subject TEXT, description TEXT, status TEXT, created_at REAL, priority TEXT DEFAULT 'low')")
conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user_id TEXT UNIQUE, password_hash TEXT)")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(tickets)")
cols = [col[1] for col in cursor.fetchall()]
if "created_at" not in cols:
    conn.execute("ALTER TABLE tickets ADD COLUMN created_at REAL")
if "priority" not in cols:
    conn.execute("ALTER TABLE tickets ADD COLUMN priority TEXT DEFAULT 'low'")
conn.commit()
conn.close()

def make_token(user_id, role):
    payload = user_id + ":" + role
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = payload + ":" + sig
    return base64.b64encode(raw.encode()).decode()

def verify_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    raw = base64.b64decode(token.encode()).decode()
    parts = raw.split(":")
    if len(parts) != 3:
        return None
    user_id, role, sig = parts[0], parts[1], parts[2]
    expected = hmac.new(SECRET.encode(), (user_id + ":" + role).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id, role

@app.route("/auth/verify", methods=["GET"])
def verify_route():
    result = verify_token(request.headers.get("Authorization"))
    if result is None:
        return jsonify({"valid": False}), 401
    user_id, role = result
    return jsonify({"valid": True, "user_id": user_id, "role": role}), 200

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "").strip()
    if not user_id or not password:
        return jsonify({"error": "user_id and password required"}), 400
    if user_id == ADMIN_USER:
        return jsonify({"error": "reserved"}), 400
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        db.close()
        return jsonify({"error": "user already exists"}), 409
    cursor.execute("INSERT INTO users (user_id, password_hash) VALUES (?, ?)", (user_id, password_hash))
    db.commit()
    db.close()
    token = make_token(user_id, "user")
    return jsonify({"token": token, "role": "user", "user_id": user_id}), 201

def is_bcrypt_hash(password_hash):
    return isinstance(password_hash, str) and password_hash.startswith("$2")

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "").strip()
    if user_id == ADMIN_USER and password == ADMIN_PASS:
        token = make_token(ADMIN_USER, "admin")
        return jsonify({"token": token, "role": "admin", "user_id": ADMIN_USER}), 200
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        db.close()
        return jsonify({"error": "invalid credentials"}), 401
    stored_hash = row[0]
    if is_bcrypt_hash(stored_hash):
        valid = bcrypt.checkpw(password.encode(), stored_hash.encode())
    else:
        valid = hashlib.sha256(password.encode()).hexdigest() == stored_hash
        if valid:
            new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, user_id))
            db.commit()
    db.close()
    if not valid:
        return jsonify({"error": "invalid credentials"}), 401
    token = make_token(user_id, "user")
    return jsonify({"token": token, "role": "user", "user_id": user_id}), 200

@app.route("/tickets", methods=["POST"])
def create_ticket():
    result = verify_token(request.headers.get("Authorization"))
    if result is None:
        return jsonify({"error": "unauthorized"}), 401
    user_id, role = result
    if role == "admin":
        return jsonify({"error": "admins cannot create tickets"}), 403
    data = request.json
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("INSERT INTO tickets (user_id, subject, description, status, created_at, priority) VALUES (?, ?, ?, 'OPEN', ?, 'low')", (user_id, data["subject"], data["description"], time.time()))
    db.commit()
    ticket_id = cursor.lastrowid
    db.close()
    return jsonify({"ticket_id": str(ticket_id), "status": "OPEN"}), 201

@app.route("/tickets/user/me", methods=["GET"])
def get_my_tickets():
    result = verify_token(request.headers.get("Authorization"))
    if result is None:
        return jsonify({"error": "unauthorized"}), 401
    user_id, role = result
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, user_id, subject, description, status, created_at, priority FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    db.close()
    tickets = []
    for row in rows:
        tickets.append({"ticket_id": str(row[0]), "user_id": row[1], "subject": row[2], "description": row[3], "status": row[4], "created_at": row[5], "priority": row[6]})
    return jsonify(tickets), 200

# --- NEW ADMIN ROUTE TO GET ALL TICKETS ---
@app.route("/tickets", methods=["GET"])
def get_all_tickets():
    result = verify_token(request.headers.get("Authorization"))
    if result is None:
        return jsonify({"error": "unauthorized"}), 401
    user_id, role = result
    if role != "admin":
        return jsonify({"error": "forbidden"}), 403
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, user_id, subject, description, status, created_at, priority FROM tickets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    db.close()
    tickets = []
    for row in rows:
        tickets.append({"ticket_id": str(row[0]), "user_id": row[1], "subject": row[2], "description": row[3], "status": row[4], "created_at": row[5], "priority": row[6]})
    return jsonify(tickets), 200
# ------------------------------------------

@app.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    result = verify_token(request.headers.get("Authorization"))
    if result is None:
        return jsonify({"error": "unauthorized"}), 401
    user_id, role = result
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, user_id, subject, description, status, created_at, priority FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    if role != "admin" and row[1] != user_id:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"ticket_id": str(row[0]), "user_id": row[1], "subject": row[2], "description": row[3], "status": row[4], "created_at": row[5], "priority": row[6]}), 200

@app.route("/tickets/<ticket_id>", methods=["PATCH"])
def update_ticket_status(ticket_id):
    data = request.json
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    updates = []
    params = []
    if "status" in data:
        updates.append("status = ?")
        params.append(data["status"])
    if "priority" in data:
        updates.append("priority = ?")
        params.append(data["priority"])
    if updates:
        params.append(ticket_id)
        cursor.execute("UPDATE tickets SET " + ", ".join(updates) + " WHERE id = ?", tuple(params))
        db.commit()
    db.close()
    return jsonify({"ticket_id": ticket_id, "status": data.get("status", "")}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)