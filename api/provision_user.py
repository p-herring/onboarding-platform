from flask_cors import CORS

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from auth.mock_auth import get_mock_user
import json
from pathlib import Path
from graph_calls import create_user, assign_license, add_to_group, send_welcome_email

app = Flask(__name__)
CORS(app)

@app.route("/api/provision_user", methods=["POST"])
def provision_user():
    user_context = get_mock_user()
    tenant_id = user_context["tenant_id"]

    with open("tenant_map.json") as f:
        tenant_map = json.load(f)

    if tenant_id not in tenant_map:
        return jsonify({"error": "Unauthorized tenant."}), 403
    
    client_key = tenant_map[tenant_id]
    config_path = Path("config") / f"{client_key}.json"
    with open(config_path) as f:
        cfg = json.load(f)

    role = request.form.get("role")
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    email = f"{first.lower()}.{last.lower()}@{cfg['domain']}"

    #Build user object
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

    user_response = create_user("mock_token", user_data)
    user_id = user_response.get("id")

    for sku in cfg["roles"][role]["licenses"]:
        assign_license("mock_token", user_id, sku)

    for group in cfg["roles"][role]["groups"]:
        add_to_group("mock_token", user_id, group)

    send_welcome_email(email)

    # Log
    log_entry = {
        "user": email,
        "role": role,
        "by": user_context["email"]
    }
    with open("logs/onboarding_log.json", "a") as log:
        log.write(json.dumps(log_entry) + "\n")

    from flask import redirect

    return jsonify({"status": "Provisioned", "user": email})

if __name__ =="__main__":
    app.run(debug=True)