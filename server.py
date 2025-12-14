from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
from notifier import notify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

@app.route("/check")
def check():
    key = request.args.get("key")
    machine = request.args.get("machine")

    if not key or not machine:
        return jsonify({"status": "error", "message": "Missing key or machine"}), 400

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT active, expires_at, machine_id FROM licenses WHERE license_key=%s", (key,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify({"status": "invalid"})

    active, expires, stored_machine = row

    if not active:
        cur.close()
        conn.close()
        return jsonify({"status": "inactive"})

    if datetime.utcnow() > expires:
        cur.close()
        conn.close()
        return jsonify({"status": "expired"})

    if stored_machine and stored_machine != machine:
        notify(f"🚨 License misuse\nKey: {key}\nOld: {stored_machine}\nNew: {machine}")
        cur.close()
        conn.close()
        return jsonify({"status": "machine_mismatch"})

    if not stored_machine:
        cur.execute("UPDATE licenses SET machine_id=%s WHERE license_key=%s", (machine, key))
        conn.commit()

    cur.close()
    conn.close()
    return jsonify({"status": "active", "expires": expires.isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
