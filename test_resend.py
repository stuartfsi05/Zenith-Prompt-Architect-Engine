import httpx
import asyncio

async def test_resend():
    RESEND_API_KEY = "re_dkRMVHDN_B4dqD4cB4vH9HPATzALnNEkD"
    
    print("Testing Resend API key...")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            json={
                "from": "Zenith Feedback <onboarding@resend.dev>",
                "to": "stuart_fsi05@hotmail.com",
                "subject": "Teste Resend - Zenith Feedback System",
                "html": "<h2>Teste do Zenith</h2><p>Se voce recebeu esse email, a integracao com o Resend esta funcionando!</p>",
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RESEND_API_KEY}",
            },
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_resend())
