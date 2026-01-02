import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API Key found")
    exit(1)

client = genai.Client(api_key=api_key)

print("🔍 Checking available models for your API Key...")
try:
    # 简单的遍历打印，不查具体属性了，防止报错
    for m in client.models.list():
        print(f"✅ Found: {m.name}")
except Exception as e:
    print(f"❌ Error listing models: {e}")
