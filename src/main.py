import logging
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

# --- 1. 路径配置 ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import Benefit, CreditCard, UserProfile
from src.tools.search import search_credit_card_info

# 只显示严重错误
logging.basicConfig(level=logging.ERROR)

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found in .env file")
    exit(1)

# 初始化客户端
client = genai.Client(api_key=api_key)


# --- 2. 模拟用户数据 ---
def init_demo_user():
    user = UserProfile(user_id="owner_001")
    cf = CreditCard(
        bank="Chase", name="Freedom Flex", network="Mastercard", last_four="1234"
    )
    cf.add_benefit(
        Benefit(
            "Quarterly 5%",
            "rotation",
            "5% cashback on rotating categories",
            "quarterly",
            1500.0,
        )
    )
    user.add_card(cf)

    plat = CreditCard(bank="Amex", name="Platinum", network="Amex", last_four="9999")
    plat.add_benefit(
        Benefit("Uber Cash", "transport", "$15 monthly credit", "monthly", 15.0)
    )
    plat.add_benefit(
        Benefit(
            "Airline Fee", "travel", "$200 annual incidental credit", "annual", 200.0
        )
    )
    user.add_card(plat)
    return user


# --- 3. System Prompt ---
SYSTEM_INSTRUCTION = """
You are Walle, an expert credit card benefit maximizer agent.
User Context: {user_summary}

Tools:
- Use `search_credit_card_info` for quarterly categories (Freedom/Discover) and specific "DPs".
- If searching for DPs/Tricks (e.g. UA Travel Bank), try mixed English/Chinese queries.

Tone: Helpful, concise, witty.
"""


# --- 4. 辅助函数：带重试的调用 (针对 Pro 模型优化) ---
def generate_content_with_retry(model_name, contents, config, max_retries=3):
    """如果遇到 429 限流，自动等待并重试"""
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model_name, contents=contents, config=config
            )
        except ClientError as e:
            # 检查是否是 429 错误
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                # Pro 模型的冷却时间较长，我们将基础等待时间调大一点 (10秒起步)
                wait_time = 10 * (attempt + 1)
                print(
                    f"   (⚠️ Pro Quota limit hit. Thinking deeply... Retrying in {wait_time}s...)"
                )
                time.sleep(wait_time)
            else:
                # 其他错误直接抛出
                raise e
    raise Exception("Max retries exceeded. The API is too busy.")


# --- 5. 主循环 ---
def main():
    user = init_demo_user()
    tools = [search_credit_card_info]

    print(f"\n🤖 Walle (v0.3 Pro Edition) | User: {len(user.cards)} Cards")
    print("-" * 50)

    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["quit", "exit"]:
                break
            if not user_input:
                continue

            print("   (Walle is thinking...) ⏳")

            # 🌟 切换到 Pro 模型
            response = generate_content_with_retry(
                model_name="gemini-flash-latest",  # <--- 这里使用了 Pro
                contents=chat_history + [user_input],
                config=types.GenerateContentConfig(
                    tools=tools,
                    system_instruction=SYSTEM_INSTRUCTION.format(
                        user_summary=user.get_summary()
                    ),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=False
                    ),
                ),
            )

            print(f"Walle: {response.text}")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
