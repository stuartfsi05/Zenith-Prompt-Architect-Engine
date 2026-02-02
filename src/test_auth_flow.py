import os
import time
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
import json

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Supabase credentials missing.")
    exit(1)

supabase: Client = create_client(url, key)

email = f"zenith_test@gmail.com"
password = "testpassword123"

# Try sign in, if fails, sign up
session = None
try:
    print("Attempting sign in...")
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    session = res.session
except Exception as e:
    print(f"Sign in failed: {e}. Attempting sign up...")
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        session = res.session
        if not session:
             print("Signed up but no session. Check email confirmation.")
             exit(1)
    except Exception as e:
        print(f"Sign up failed: {e}")
        exit(1)

token = session.access_token
print(f"Got token: {token}")

# Call API
headers = {"Authorization": f"Bearer {token}"}
data = {"message": "Hello usage test", "session_id": "usage_test_session"}

print("Sending request to API...")
try:
    response = requests.post("http://127.0.0.1:8000/chat", json=data, headers=headers, stream=True)
    print("Response status:", response.status_code)
    
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))
    else:
        print(response.text)
        
except Exception as e:
    print(f"Request failed: {e}")
