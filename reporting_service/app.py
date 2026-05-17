from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

db_path = "/data/reporting.db"
os.makedirs("/data", exist_ok=True)
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, ticket_id TEXT, event_type TEXT, time_taken_minutes REAL)")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(metrics)")
columns = [col[1] for col in cursor.fetchall()]
if "opened_at" not in columns:
    conn.execute("ALTER TABLE metrics ADD COLUMN opened_at REAL")
if "resolved_at" not in columns:
    conn.execute("ALTER TABLE metrics ADD COLUMN resolved_at REAL")
conn.commit()
conn.close()

@app.route("/metrics", methods=["POST"])
def log_metric():
    data = request.json
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    # Insert metric record
    cursor.execute("INSERT INTO metrics (ticket_id, event_type, time_taken_minutes, opened_at, resolved_at) VALUES (?, ?, ?, ?, ?)", (data["ticket_id"], data["event_type"], data["time_taken_minutes"], data.get("opened_at"), data.get("resolved_at")))
    db.commit()
    db.close()
    return jsonify({"status": "recorded"}), 201

@app.route("/metrics", methods=["GET"])
def get_metrics():
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    # Count distinct tickets and average resolution time
    cursor.execute("SELECT COUNT(DISTINCT ticket_id), AVG(time_taken_minutes) FROM metrics")
    row = cursor.fetchone()
    db.close()
    total = row[0] if row[0] else 0
    avg_time = row[1] if row[1] else 0.0
    return jsonify({"total_tickets": total, "average_resolution_time": avg_time}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
