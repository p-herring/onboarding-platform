def create_user(token, user_data):
    print(f"[MOCK] Creating user: {user_data['userPrincipalName']}")
    return {"id": "mock_user_id_123"}

def assign_license(token, user_id, sku_id):
    print(f"[MOCK] Assigning license {sku_id} to user {user_id}")
    return {"status": "success"}

def add_to_group(token, user_id, group_id):
    print(f"[MOCK] Adding user {user_id} to user {group_id}")
    return {"status": "success"}

def send_welcome_email(user_email): #add managers email aswell
    print(f"[MOCK] Sending welcome email to {user_email}")
    return {"status": "sent"}