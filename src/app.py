import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from src.storage import delete_card_from_db, load_user_data, save_new_card

# --- 数据预设：全美主流银行与热门卡片 (参考 USCreditCardGuide) ---
POPULAR_CARDS = {
    "Chase": [
        "Sapphire Preferred",
        "Sapphire Reserve",
        "Freedom Flex",
        "Freedom Unlimited",
        "Freedom Rise",
        "Ink Business Preferred",
        "Ink Business Cash",
        "Ink Business Unlimited",
        "Ink Business Premier",
        "United Explorer",
        "United Quest",
        "United Club Infinite",
        "Marriott Bonvoy Boundless",
        "Marriott Bonvoy Bold",
        "Ritz-Carlton",
        "World of Hyatt",
        "World of Hyatt Business",
        "IHG One Rewards Premier",
        "IHG One Rewards Traveler",
        "Aeroplan",
        "British Airways",
        "Southwest Priority",
    ],
    "Amex": [
        "Platinum",
        "Gold",
        "Green",
        "Blue Cash Preferred",
        "Blue Cash Everyday",
        "EveryDay Preferred",
        "Business Platinum",
        "Business Gold",
        "Blue Business Plus",
        "Delta SkyMiles Gold",
        "Delta SkyMiles Platinum",
        "Delta SkyMiles Reserve",
        "Hilton Honors Aspire",
        "Hilton Honors Surpass",
        "Hilton Honors",
        "Marriott Bonvoy Brilliant",
        "Marriott Bonvoy Bevy",
    ],
    "Citi": [
        "Strata Premier",
        "Double Cash",
        "Custom Cash",
        "Rewards+",
        "Costco Anywhere",
        "Simplicity",
        "Diamond Preferred",
        "AAdvantage Platinum Select",
        "AAdvantage Executive",
        "AAdvantage MileUp",
    ],
    "Capital One": [
        "Venture X",
        "Venture",
        "VentureOne",
        "Savor",
        "SavorOne",
        "Quicksilver",
        "QuicksilverOne",
        "Spark Cash Plus",
        "Spark Miles",
    ],
    "BoA (Bank of America)": [
        "Customized Cash Rewards",
        "Unlimited Cash Rewards",
        "Premium Rewards",
        "Premium Rewards Elite",
        "Travel Rewards",
        "Alaska Airlines Visa",
    ],
    "US Bank": [
        "Altitude Reserve",
        "Altitude Connect",
        "Altitude Go",
        "Cash+",
        "Shopper Cash Rewards",
        "FlexPerks Gold",
    ],
    "Wells Fargo": [
        "Autograph Journey",
        "Autograph",
        "Active Cash",
        "Reflect",
        "Attune",
        "Bilt Mastercard",  # Bilt 其实是 WF 发行的，但也常单独列出
    ],
    "Barclays": [
        "AAdvantage Aviator Red",
        "JetBlue Plus",
        "Wyndham Rewards Earner",
        "Hawaiian Airlines",
    ],
    "Discover": ["It Cash Back", "It Miles", "It Chrome"],
    "Bilt": ["Bilt Mastercard"],
    "Other": [],  # 兜底选项
}

# --- 1. 路径配置 (确保能找到 src 下的模块) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import CreditCard
from src.tools.search import search_credit_card_info

# --- 2. 页面配置 ---
st.set_page_config(
    page_title="Walle AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
# --- 🌟 界面美化 (Custom CSS) ---
st.markdown(
    """
<style>
    /* 1. 全局字体与间距优化 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* 2. 聊天气泡美化 */
    .stChatMessage {
        background-color: #1E2329;
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #30363D;
    }
    
    /* 3. 按钮样式 - 圆角与渐变 */
    .stButton button {
        border-radius: 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2);
    }

    /* 4. 输入框美化 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px;
    }
    
    /* 5. 侧边栏标题美化 */
    [data-testid="stSidebar"] h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #FFC107, #FF8F00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 加载环境变量
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


# --- 辅助函数：根据网络显示图标 ---
def get_network_icon(network):
    icons = {
        "Visa": "💳",  # 或者用 emoji "🇻"
        "Mastercard": "🟠",
        "Amex": "🦅",
        "Discover": "🔭",
    }
    return icons.get(network, "💳")


# --- 3. 初始化 Session State (记忆) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 🔥 核心修改：不再使用 hardcoded 数据，而是从 Google Sheets 加载
if "user_profile" not in st.session_state:
    with st.spinner("Connecting to Walle Brain (Database)..."):
        # 默认加载 owner_001 的数据
        st.session_state.user_profile = load_user_data(user_id="owner_001")
# --- 侧边栏设计 (重构版) ---
with st.sidebar:
    st.title("🤖 Walle Brain")
    st.caption("Your Personal Finance Agent")
    st.markdown("---")

    # === A. My Wallet (卡片列表) ===
    st.subheader("💳 Your Wallet")

    user = st.session_state.user_profile
    if not user.cards:
        st.warning("No cards loaded.")
    else:
        for i, card in enumerate(user.cards):
            icon = get_network_icon(card.network)
            # 使用更紧凑的显示方式
            with st.container():
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**{card.bank} {card.name}**")
                    st.caption(f"{icon} {card.network} • *{card.last_four}*")
                with col2:
                    if st.button("✕", key=f"del_{i}", help="Remove Card"):
                        # 🔥 1. 先从云端数据库删除
                        delete_card_from_db("owner_001", i)

                        # 2. 再从本地删除
                        user.cards.pop(i)
                        st.rerun()
                st.markdown("---")  # 分割线

    # === B. Add New Card (交互式表单) ===
    with st.expander("➕ Add New Card", expanded=False):
        # 1. 选择银行 (Bank)
        bank_options = list(POPULAR_CARDS.keys())
        selected_bank = st.selectbox("Bank", bank_options, index=0)

        # 处理 "Other" 银行的情况
        if selected_bank == "Other":
            final_bank = st.text_input("Enter Bank Name", placeholder="e.g. Synchrony")
        else:
            final_bank = selected_bank

        # 2. 选择卡片 (Card Name)
        card_list = POPULAR_CARDS.get(selected_bank, [])
        card_options = card_list + ["Other / Type Manually"]

        selected_card_name = st.selectbox("Card Name", card_options)

        if selected_card_name == "Other / Type Manually":
            final_card_name = st.text_input(
                "Enter Card Name", placeholder="e.g. Autograph"
            )
        else:
            final_card_name = selected_card_name

        # 3. 网络与尾号 (并排显示)
        col_net, col_last4 = st.columns(2)

        with col_net:
            # 增加 "Unknown" 选项，并将其作为默认
            network_options = ["Unknown", "Visa", "Mastercard", "Amex", "Discover"]

            # 智能推断逻辑 (仅针对非常确定的情况)
            default_idx = 0  # 默认为 "Unknown"

            if final_bank == "Amex":
                default_idx = 3  # Amex 在列表中的索引是 3
            elif final_bank == "Discover":
                default_idx = 4  # Discover 在列表中的索引是 4
            elif final_bank == "Bilt":
                default_idx = 2  # Mastercard
            # 对于 Chase/Citi 这种既有 Visa 又有 Mastercard 的，保持 Unknown 让用户省心

            final_network = st.selectbox(
                "Network (Optional)", network_options, index=default_idx
            )

        with col_last4:
            # 尾号输入 (可选)
            last_four_input = st.text_input(
                "Last 4 (Optional)", max_chars=4, placeholder="8888"
            )
            final_last_four = last_four_input if last_four_input else "0000"

        # 4. 添加按钮
        if st.button("Add to Wallet", use_container_width=True):
            if final_bank and final_card_name:
                new_card = CreditCard(
                    bank=final_bank,
                    name=final_card_name,
                    network=final_network,
                    last_four=final_last_four,
                )

                # 🔥 1. 先保存到云端数据库
                save_new_card("owner_001", new_card)

                # 2. 再更新本地 Session State (为了即时显示，不用重新拉取数据库)
                st.session_state.user_profile.add_card(new_card)

                st.success(f"Added {final_bank} {final_card_name}!")
                time.sleep(0.5)
                st.rerun()

    # === C. Reset ===
    if st.button("🔄 Reset Demo", use_container_width=True):
        del st.session_state.user_profile
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


# 渲染历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("E.g., Which card for dining tonight?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Thinking...", expanded=False) as status:
            response = generate_response_with_retry(
                prompt, st.session_state.messages[:-1]
            )
            status.update(label="Done", state="complete")
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
