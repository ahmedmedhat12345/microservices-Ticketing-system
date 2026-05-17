from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests
import time

app = Flask(__name__)
CORS(app)

db_path = "/data/support.db"
os.makedirs("/data", exist_ok=True)
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY, ticket_id TEXT, agent_id TEXT, response TEXT, status TEXT, timestamp REAL)")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(support)")
cols = [col[1] for col in cursor.fetchall()]
if "timestamp" not in cols:
    conn.execute("ALTER TABLE support ADD COLUMN timestamp REAL")
conn.commit()
conn.close()

def check_admin(auth_header):
    # verify token via ticket_service and confirm role is admin
    res = requests.get("http://ticket-service:5000/auth/verify", headers={"Authorization": auth_header})
    if res.status_code != 200:
        return None
    data = res.json()
    if data.get("role") != "admin":
        return None
    return data.get("user_id")

@app.route("/support", methods=["POST"])
def add_support_interaction():
    auth_header = request.headers.get("Authorization", "")
    agent = check_admin(auth_header)
    if agent is None:
        return jsonify({"error": "admin only"}), 403
    data = request.json
    ticket_resp = requests.get(f"http://ticket-service:5000/tickets/{data['ticket_id']}", headers={"Authorization": auth_header}).json()
    
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("INSERT INTO support (ticket_id, agent_id, response, status, timestamp) VALUES (?, ?, ?, ?, ?)", (data["ticket_id"], agent, data["response"], data["new_status"], time.time()))
    db.commit()
    interaction_id = cursor.lastrowid
    db.close()
    
    patch_data = {"status": data["new_status"]}
    if "new_priority" in data and data["new_priority"]:
        patch_data["priority"] = data["new_priority"]
    requests.patch(f"http://ticket-service:5000/tickets/{data['ticket_id']}", json=patch_data)
    
    if data["new_status"] == "RESOLVED":
        opened_at = float(ticket_resp.get("created_at", time.time()))
        resolved_at = time.time()
        duration = (resolved_at - opened_at) / 60.0
        requests.post("http://reporting-service:5002/metrics", json={"ticket_id": data["ticket_id"], "event_type": "RESOLUTION", "time_taken_minutes": duration, "opened_at": opened_at, "resolved_at": resolved_at})
    
    # --- The Magic Notification Edit ---
    # Formatting the message to include Ticket ID and the New Status
    detailed_message = f"Ticket #{data['ticket_id']} [{data['new_status']}]: {data['response']}"
    
    requests.post("http://notification-service:5003/notifications", json={
        "user_id": ticket_resp["user_id"], 
        "message": detailed_message
    })
    
    return jsonify({"interaction_id": str(interaction_id), "status": data["new_status"]}), 201

@app.route("/support/<ticket_id>", methods=["GET"])
def get_ticket_history(ticket_id):
    auth_header = request.headers.get("Authorization", "")
    # verify token via ticket_service — it enforces ownership there
    verify_res = requests.get("http://ticket-service:5000/auth/verify", headers={"Authorization": auth_header})
    if verify_res.status_code != 200:
        return jsonify({"error": "unauthorized"}), 401
    token_data = verify_res.json()
    role = token_data.get("role")
    user_id = token_data.get("user_id")
    
    if role != "admin":
        # confirm this user owns the ticket before returning history
        ticket_res = requests.get(f"http://ticket-service:5000/tickets/{ticket_id}", headers={"Authorization": auth_header})
        if ticket_res.status_code == 403:
            return jsonify({"error": "forbidden"}), 403
        if ticket_res.status_code == 404:
            return jsonify({"error": "not found"}), 404
            
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT id, agent_id, response, status, timestamp FROM support WHERE ticket_id = ? ORDER BY timestamp ASC", (ticket_id,))
    rows = cursor.fetchall()
    db.close()
    
    history = []
    for row in rows:
        history.append({"id": row[0], "agent_id": row[1], "response": row[2], "status": row[3], "timestamp": row[4]})
    return jsonify(history), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)