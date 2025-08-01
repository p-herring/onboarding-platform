import json
from graph_calls import create_user, assign_license, add_to_group, send_welcome_email
from pathlib import Path

#==================================
#LOAD CLIENT CONFIG
#==================================
client = "acme" #change to dynamic later
config_path = Path("config") / f"{client}.json"
with open(config_path) as f:
    cfg = json.load(f)


#==================================
#GET USER INPUT
#==================================
print(f"\n--- {cfg['company']} New User Onboarding ---")
first = input("First Name: ")
last = input("Last Name: ")
role = input(f"Role ({'/'.join(cfg['roles'].keys())}): ")
email = f"{first.lower()}.{last.lower()}@{cfg['domain']}"

#==================================
#BUILD USER OBJECT
#==================================
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

#==================================
#MOCK API CALLS
#==================================
print("\n--- Executing Provisioning ---")
user_response = create_user("mock_token", user_data)
user_id = user_response.get("id")

for sku in cfg["roles"][role]["licenses"]:
    assign_license("mock_token", user_id, sku)

for group in cfg["roles"][role]["groups"]:
    add_to_group("mock_token", user_id, group)

if cfg["security"]["mfa_required"]:
    print(f"[MOCK] MFA enforced for {email}")

send_welcome_email(email)

#==================================
#LOG RESULT
#==================================
log_entry = {
    "user": email,
    "role": role,
    "groups": cfg["roles"][role]["groups"],
    "licenses": cfg["roles"][role]["licenses"]
}
log_file = Path("logs") / "onboarding_log.json"
with open(log_file, "a") as log:
    log.write(json.dumps(log_entry) + "\n")

print(f"\n✅ Onboarding complete for {email}\n")

#==================================
#NEXT STEPS
#==================================
# - Add support for multiple clients
# - Add argument parsing (e.g. `--client acme --role Manager`)
# - Replace mock calls with real Graph API once tenant is ready
# - Add input validation and error handling
# - Build web frontend (optional)
# - Integrate welcome email templates
# - Create offboarding companion script
