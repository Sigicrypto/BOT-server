# server/server.py
from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from notifier import notify
import os

app = Flask(__name__)

DB_PATH = "licenses.db"  # note: will reset on free Render restart


def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@app.route("/check")
def check():
    key = request.args.get("key")
    machine = request.args.get("machine")

    cur = db().cursor()
    cur.execute("SELECT active, expires_at, machine_id FROM licenses WHERE license_key=?", (key,))
    row = cur.fetchone()

    if not row:
        return jsonify({"status": "invalid"})

    active, expires, stored_machine = row

    if not active:
        return jsonify({"status": "inactive"})

    if datetime.utcnow() > datetime.fromisoformat(expires):
        return jsonify({"status": "expired"})

    if stored_machine and stored_machine != machine:
        notify(f"🚨 License misuse\nKey: {key}\nOld: {stored_machine}\nNew: {machine}")
        return jsonify({"status": "machine_mismatch"})

    if not stored_machine:
        db().execute("UPDATE licenses SET machine_id=? WHERE license_key=?", (machine, key))
        db().commit()

    return jsonify({"status": "active", "expires": expires})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
