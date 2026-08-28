import asyncio
import httpx
import sys
import os

# Include parent path to load backend configurations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import settings

async def test_groq_payload(char_count: int):
    print(f"Testing Groq payload with {char_count} characters of document context...")
    
    # Generate mock context text
    dummy_context = "This is educational content. " * (char_count // 25)
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.GROQ_API_KEY}"
    }
    
    prompt = f"Summarize the following educational content in strict JSON: {dummy_context}"
    
    payload = {
        "model": settings.MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that returns JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.post(url, json=payload, headers=headers)
            print(f"Status Code: {res.status_code}")
            if res.status_code == 200:
                print("SUCCESS!")
            else:
                print(f"FAILED: {res.text}")
        except Exception as e:
            print(f"Error calling API: {e}")

async def main():
    print(f"Using Groq Model: {settings.MODEL_NAME}")
    # Test different character limits
    for count in [1000, 2000, 3000, 4000, 8000]:
        await test_groq_payload(count)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
