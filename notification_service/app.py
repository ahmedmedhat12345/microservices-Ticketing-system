from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

db_path = "/data/notification.db"
os.makedirs("/data", exist_ok=True)
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, user_id TEXT, message TEXT, status TEXT)")
conn.commit()
conn.close()

@app.route("/notifications", methods=["POST"])
def send_notification():
    data = request.json
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("INSERT INTO notifications (user_id, message, status) VALUES (?, ?, 'SENT')", (data["user_id"], data["message"]))
    db.commit()
    last_id = cursor.lastrowid
    db.close()
    return jsonify({"notification_id": str(last_id), "status": "SENT"}), 201

@app.route("/notifications", methods=["GET"])
def get_all_notifications():
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, user_id, message, status FROM notifications")
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"id": r[0], "user_id": r[1], "message": r[2], "status": r[3]} for r in rows]), 200

@app.route("/notifications/user/<user_id>", methods=["GET"])
def get_user_notifications(user_id):
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, user_id, message, status FROM notifications WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"id": r[0], "user_id": r[1], "message": r[2], "status": r[3]} for r in rows]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
