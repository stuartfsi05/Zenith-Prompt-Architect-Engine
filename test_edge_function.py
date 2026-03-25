import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_edge_function():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    edge_url = f"{supabase_url}/functions/v1/send-feedback"
    
    print(f"Testing Edge Function at: {edge_url}")
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            edge_url,
            json={
                "user_email": "stuart_fsi05@hotmail.com",
                "message": "Teste automatizado da Edge Function de feedback. Se você recebeu isso, a integração via HTTP funcionou perfeitamente!",
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {supabase_key}",
            },
        )
        
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_edge_function())
