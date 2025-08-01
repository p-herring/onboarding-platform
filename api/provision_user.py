import csv
from flask import render_template
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.mock_auth import get_mock_user
from graph_calls import create_user, assign_license, add_to_group, send_welcome_email

app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app)

CSV_FILE = Path("logs/onboarded_users.csv")
LOG_FILE = Path("logs/onboarding_log.json")
CREATED_USERS = set()

# Load CSV to track existing users
if CSV_FILE.exists():
    with open(CSV_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            CREATED_USERS.add(row["email"])

@app.route("/success")
def success():
    status = request.args.get("status")
    user = request.args.get("user")
    return render_template("success.html", status=status, user=user)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/client_config")
def client_config():
    user_context = get_mock_user()
    tenant_id = user_context["tenant_id"]

    try:
        with open("tenant_map.json") as f:
            tenant_map = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "tenant_map.json not found."}), 500

    client_key = tenant_map.get(tenant_id)
    if not client_key:
        return jsonify({"error": "Unauthorized tenant."}), 403

    config_path = Path("config") / f"{client_key}.json"
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": f"Config for client '{client_key}' not found."}), 500

    return jsonify({
    "features": list(cfg.get("features", {}).keys())
    })

@app.route("/api/provision_user", methods=["POST"])
def provision_user():
    user_context = get_mock_user()
    tenant_id = user_context["tenant_id"]

    try:
        with open("tenant_map.json") as f:
            tenant_map = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "tenant_map.json not found."}), 500

    #if tenant_id not in tenant_map:
        #return jsonify({"error": "Unauthorized tenant."}), 403

    client_key = tenant_map[tenant_id]
    config_path = Path("config") / f"{client_key}.json"

    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": f"Config for client '{client_key}' not found."}), 500

    license_type = request.form.get("license_type")
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    email = f"{first.lower()}.{last.lower()}@{cfg['domain']}"

    selected_features = request.form.get("selected_features")
    if selected_features:
        features = json.loads(selected_features)
    # log them, or use them as needed per client


    if email in CREATED_USERS:
        log_status("duplicate", email, license_type, user_context["email"])
        return jsonify({"error": "User already exists."}), 409

    # Build user object
    user_data = {
        "accountEnabled": True,
        "displayName": f"{first} {last}",
        "mailNickname": f"{first}.{last}",
        "userPrincipalName": email,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": cfg["default_password"]
        }
    }

    try:
        user_response = create_user("mock_token", user_data)
        user_id = user_response.get("id")
        for sku in cfg["license_type"][license_type]["licenses"]:
            assign_license("mock_token", user_id, sku)
        for group in cfg["license_type"][license_type]["groups"]:
            add_to_group("mock_token", user_id, group)
        send_welcome_email(email)

        CREATED_USERS.add(email)
        log_status("success", email, license_type, user_context["email"])
        return jsonify({"status": "Provisioned", "user": email})

    except Exception as e:
        log_status("error", email, license_type, user_context["email"], str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

def log_status(status, email, license_type, requested_by, error=None):
    timestamp = datetime.utcnow().isoformat() + "Z"

    # JSON log
    log_entry = {
        "timestamp": timestamp,
        "status": status,
        "user": email,
        "license_type": license_type,
        "requested_by": requested_by
    }
    if error:
        log_entry["error"] = error

    with open(LOG_FILE, "a") as log:
        log.write(json.dumps(log_entry) + "\n")

    # CSV log
    headers = ["timestamp", "email", "license_type", "requested_by", "status", "error"]
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": timestamp,
            "email": email,
            "license_type": license_type,
            "requested_by": requested_by,
            "status": status,
            "error": error or ""
        })

if __name__ == "__main__":
    app.run(debug=True)
