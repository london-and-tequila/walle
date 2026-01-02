import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

# --- 1. 路径配置 (确保能找到 src 下的模块) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import Benefit, CreditCard, UserProfile
from src.tools.search import search_credit_card_info

# --- 2. 页面配置 ---
st.set_page_config(
    page_title="Walle - Credit Card AI", page_icon="🤖", layout="centered"
)

# 加载环境变量
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# --- 3. 初始化 Session State (记忆) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_profile" not in st.session_state:
    # 初始化演示用户 (只执行一次)
    user = UserProfile(user_id="owner_001")

    cf = CreditCard(
        bank="Chase", name="Freedom Flex", network="Mastercard", last_four="1234"
    )
    cf.add_benefit(
        Benefit("Quarterly 5%", "rotation", "5% cashback", "quarterly", 1500.0)
    )
    user.add_card(cf)

    plat = CreditCard(bank="Amex", name="Platinum", network="Amex", last_four="9999")
    plat.add_benefit(
        Benefit("Uber Cash", "transport", "$15 monthly credit", "monthly", 15.0)
    )
    plat.add_benefit(
        Benefit("Airline Fee", "travel", "$200 annual credit", "annual", 200.0)
    )
    user.add_card(plat)

    st.session_state.user_profile = user

# --- 4. 侧边栏：显示用户画像 ---
with st.sidebar:
    st.title("💳 Walle's Brain")
    st.markdown("---")
    st.subheader("Current User Profile")

    user = st.session_state.user_profile
    for card in user.cards:
        with st.expander(f"{card.bank} {card.name}", expanded=True):
            st.markdown(f"**Network:** {card.network}")
            st.markdown("**Benefits:**")
            for ben in card.benefits:
                st.caption(f"• {ben.name}: ${ben.remaining_amount} left")

    st.markdown("---")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 5. 核心逻辑函数 ---


def get_gemini_client():
    return genai.Client(api_key=api_key)


def generate_response_with_retry(prompt, history):
    """调用 Gemini API，包含重试逻辑"""
    client = get_gemini_client()
    user = st.session_state.user_profile

    # 系统提示词
    SYSTEM_INSTRUCTION = f"""
    You are Walle, an expert credit card benefit maximizer agent.
    
    ### User Context (The Truth):
    {user.get_summary()}
    (Note: Only strictly follow the benefits listed above. Do not hallucinate benefits not in this list.)

    ### Critical Instructions:
    1. **ALWAYS Search First**: Before recommending a card for a specific spending category (e.g., Dining), you MUST use the `search_credit_card_info` tool to check:
       - What are the current quarterly rotating categories for Chase Freedom/Discover?
       - Are there any special limited-time offers?
       - Are there any other benefits that can be used for this spending category?
       
    2. **Math & Logic**: 
       - Calculate the "Effective Return Rate" for each card.
       - Logic for Freedom Flex: Base (1%) + Dining Bonus (2%) + Quarterly Bonus (4%) = 7% (if applicable).
       - Logic for Amex Plat: Check if any credits (Uber/Saks) can be applied.

    3. **Format**:
       - Use a clear comparison table.
       - Explain the math step-by-step.
    
    Tone: Helpful, concise, data-driven. 
    Format: Use Markdown for tables and bold text.
    """

    # 准备工具
    tools = [search_credit_card_info]

    # 构建历史消息 (简单拼接)
    contents = []
    for msg in history:
        contents.append(msg["content"])
    contents.append(prompt)

    # 尝试调用
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 这里的模型你可以换成 gemini-1.5-pro-latest 或 gemini-flash-latest
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=tools,
                    system_instruction=SYSTEM_INSTRUCTION,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=False
                    ),
                ),
            )
            return response.text

        except ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = 5 * (attempt + 1)
                # 在界面上显示等待状态
                with st.status(
                    f"⚠️ Brain overload... Cooling down for {wait_time}s...",
                    expanded=True,
                ) as status:
                    time.sleep(wait_time)
                    status.update(label="Retrying...", state="running")
            else:
                return f"❌ Error: {str(e)}"

    return "❌ System Error: Max retries exceeded. The API is too busy."


# --- 6. 聊天界面渲染 ---

st.title("🤖 Walle: Credit Card Agent")
st.caption(
    "Ask me about quarterly categories, rewards optimization, or spending tricks."
)

# 渲染历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("How can I maximize my points today?"):
    # 1. 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 显示助手正在思考
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        # 使用 status 容器显示思考过程 (模拟联网搜索的感觉)
        with st.status("Thinking & Searching...", expanded=False) as status:
            full_response = generate_response_with_retry(
                prompt, st.session_state.messages[:-1]
            )
            status.update(label="Done!", state="complete", expanded=False)

        # 显示最终回复
        message_placeholder.markdown(full_response)

    # 3. 保存助手消息
    st.session_state.messages.append({"role": "assistant", "content": full_response})
