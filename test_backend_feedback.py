import httpx
import asyncio

async def test_backend():
    print("Testing local FastAPI backend /feedback endpoint...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First login to get a token
        print("Authenticating...")
        login_res = await client.post(
            "http://localhost:8000/auth/login",
            json={"email": "stuart_fsi05@hotmail.com", "password": "123456"}
        )
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code}")
            return
            
        token = login_res.json()["access_token"]
        
        # Test feedback
        print("Sending feedback...")
        fb_res = await client.post(
            "http://localhost:8000/feedback",
            json={"message": "Integrated backend test to Edge Function"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status: {fb_res.status_code}")
        print(f"Response: {fb_res.text}")

if __name__ == "__main__":
    asyncio.run(test_backend())
