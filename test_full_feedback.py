import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_full_flow():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    edge_url = f"{supabase_url}/functions/v1/send-feedback"
    
    print(f"=== TESTE COMPLETO DO FLUXO DE FEEDBACK ===")
    print(f"Edge Function URL: {edge_url}")
    print()
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            edge_url,
            json={
                "user_email": "stuart_fsi05@hotmail.com",
                "message": "Teste completo do fluxo de feedback via Resend! Se este email chegou, toda a pipeline esta funcionando: Backend -> Edge Function -> Resend API -> Email.",
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {supabase_key}",
            },
        )
    
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")
    print()
    print(f"  Salvo no banco? {'SIM' if result.get('stored_in_db') else 'NAO'}")
    print(f"  Email enviado?  {'SIM' if result.get('email_sent') else 'NAO'}")
    
    if result.get('email_sent'):
        print()
        print("O email deve chegar em stuart_fsi05@hotmail.com em alguns segundos!")
    else:
        print()
        print("ATENCAO: O email NAO foi enviado. Verifique se o secret RESEND_API_KEY esta configurado corretamente.")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
