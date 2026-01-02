import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.models import CreditCard
from src.storage import (
    delete_card_from_db,
    load_user_data,
    save_new_card,
    update_card_in_db,
)
from src.tools.search import search_credit_card_info

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


# --- 1. 登录逻辑 (Sidebar) ---
def render_login_sidebar():
    """渲染侧边栏的登录/用户信息区"""
    with st.sidebar:
        st.title("🤖 Walle Login")

        # 检查 Session State 中是否有 user_id
        if "user_id" not in st.session_state:
            # === A. 未登录状态 ===
            st.info("Please enter your email to access your wallet.")

            # 使用 form 避免每输入一个字就刷新
            with st.form("login_form"):
                email_input = st.text_input(
                    "Email Address", placeholder="e.g. tony@stark.com"
                )
                submitted = st.form_submit_button("🚀 Login / Register")

                if submitted and email_input:
                    # 简单处理：把邮箱转为小写，作为唯一 ID
                    user_id = email_input.strip().lower()
                    st.session_state.user_id = user_id
                    st.success(f"Welcome, {user_id}!")
                    time.sleep(0.5)
                    st.rerun()  # 强制刷新进入已登录状态

            return None  # 返回 None 表示未登录

        else:
            # === B. 已登录状态 ===
            current_user = st.session_state.user_id
            st.success(f"👤 User: {current_user}")

            # 登出按钮
            if st.button("Logout", type="secondary"):
                # 清除状态
                del st.session_state.user_id
                if "user_profile" in st.session_state:
                    del st.session_state.user_profile
                st.rerun()

            return current_user


# 获取当前登录用户 (如果未登录，这里会中断后续渲染)
CURRENT_USER_ID = render_login_sidebar()

if not CURRENT_USER_ID:
    # 如果没登录，右侧主界面显示欢迎页，并停止执行后续代码
    st.title("Welcome to Walle AI 🤖")
    st.markdown("""
    Your personal credit card maximizer agent.
    
    👈 **Please login using your email in the sidebar to start.**
    
    *(Data is securely stored in your private Google Sheet)*
    """)
    st.stop()  # 🛑 停止执行后续代码 (非常重要！)

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

if "active_edit_index" not in st.session_state:
    st.session_state.active_edit_index = None

# 🔥 核心修改：不再使用 hardcoded 数据，而是从 Google Sheets 加载
if "user_profile" not in st.session_state:
    with st.spinner(f"Loading wallet for {CURRENT_USER_ID}..."):
        # 🔥 使用动态的 Email 作为 ID 加载数据
        st.session_state.user_profile = load_user_data(user_id=CURRENT_USER_ID)

# --- 侧边栏设计 (重构版) ---
with st.sidebar:
    st.title("🤖 Walle Brain")
    st.caption("Your Personal Finance Agent")
    st.markdown("---")

    # === A. My Wallet (卡片列表) ===
    # === A. My Wallet (卡片列表) ===
    st.subheader("💳 Your Wallet")

    user = st.session_state.user_profile
    if not user.cards:
        st.info("No cards yet. Add one below!")
    else:
        for i, card in enumerate(user.cards):
            icon = get_network_icon(card.network)

            # 这里的 Expander 只是容器
            with st.expander(
                f"{icon} {card.bank} {card.name} (...{card.last_four})", expanded=False
            ):
                # 🔄 核心逻辑：判断当前卡片是否处于编辑状态
                # 如果 active_edit_index 等于当前的 i，显示表单；否则显示详情
                if st.session_state.active_edit_index == i:
                    # === [编辑模式] ===
                    with st.form(key=f"edit_form_{i}"):
                        new_bank = st.text_input("Bank", value=card.bank)
                        new_name = st.text_input("Card Name", value=card.name)

                        col1, col2 = st.columns(2)
                        with col1:
                            nets = ["Unknown", "Visa", "Mastercard", "Amex", "Discover"]
                            curr_idx = (
                                nets.index(card.network) if card.network in nets else 0
                            )
                            new_net = st.selectbox("Network", nets, index=curr_idx)
                        with col2:
                            new_last4 = st.text_input(
                                "Last 4", value=card.last_four, max_chars=4
                            )

                        # 日期处理
                        import datetime

                        default_date = None
                        if card.open_date:
                            try:
                                default_date = datetime.datetime.strptime(
                                    card.open_date, "%Y-%m-%d"
                                ).date()
                            except:
                                pass
                        new_open_date = st.date_input("Open Date", value=default_date)

                        # 💾 保存逻辑
                        if st.form_submit_button("💾 Save"):
                            # 1. 更新数据对象
                            date_str = (
                                new_open_date.strftime("%Y-%m-%d")
                                if new_open_date
                                else ""
                            )
                            updated_card = CreditCard(
                                bank=new_bank,
                                name=new_name,
                                network=new_net,
                                last_four=new_last4,
                                open_date=date_str,
                            )

                            # 2. 更新数据库
                            update_card_in_db(CURRENT_USER_ID, i, updated_card)

                            # 3. 更新本地 Session
                            user.cards[i] = updated_card

                            # 🔥 4. 关键：保存成功后，把“当前编辑索引”设为 None，即退出编辑模式
                            st.session_state.active_edit_index = None

                            st.success("Updated!")
                            time.sleep(0.5)
                            st.rerun()

                else:
                    # === [查看模式] ===
                    st.write(f"**Network:** {card.network}")
                    st.write(f"**Last 4:** {card.last_four}")
                    st.write(
                        f"**Opened:** {card.open_date if card.open_date else 'N/A'}"
                    )

                    col_edit, col_del = st.columns([1, 1])

                    # ✏️ 这是一个普通按钮，点击后通过 callback 修改 active_edit_index
                    with col_edit:

                        def enter_edit_mode(index):
                            st.session_state.active_edit_index = index

                        st.button(
                            "✏️ Edit",
                            key=f"btn_edit_{i}",
                            on_click=enter_edit_mode,
                            args=(i,),
                        )

                    with col_del:
                        if st.button("🗑️ Del", key=f"del_{i}"):
                            delete_card_from_db(CURRENT_USER_ID, i)
                            user.cards.pop(i)
                            st.rerun()

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

        # ✨ 新增：开卡日期输入 (Optional)
        # value=None 让它默认显示为空，看起来就是 Optional 的
        open_date_input = st.date_input(
            "Card Open Date (Optional)",
            value=None,
            min_value=None,
            max_value=None,
            help="Used to calculate Chase 5/24 status.",
        )

        # 4. 添加按钮
        if st.button("Add to Wallet", use_container_width=True):
            if final_bank and final_card_name:
                final_open_date = (
                    open_date_input.strftime("%Y-%m-%d") if open_date_input else ""
                )
                new_card = CreditCard(
                    bank=final_bank,
                    name=final_card_name,
                    network=final_network,
                    last_four=final_last_four,
                    open_date=final_open_date,
                )

                # 🔥 1. 先保存到云端数据库
                save_new_card(CURRENT_USER_ID, new_card)

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


# ==========================================
# 3. 主界面 (Main Interface)
# ==========================================

# 页面标题
st.title("🤖 Walle: Credit Card Agent")
st.caption("Maximize rewards, track benefits, and master your wallet.")

# --- 🌟 功能 1: 空状态下的“建议卡片” (Hero Section) ---
if not st.session_state.messages:
    st.markdown(
        """
    <style>
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        border: 1px solid #30363D;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("### 👋 How can I help you today?")
    st.markdown("Here are a few things I can do for you:")

    # 创建 2x2 的建议网格
    col1, col2 = st.columns(2)

    # 定义点击处理函数
    def click_suggestion(text):
        st.session_state.messages.append({"role": "user", "content": text})

    with col1:
        if st.button(
            "🍔 Dining Spending", help="Ask for the best card for restaurants"
        ):
            click_suggestion(
                "I'm going out for dinner tonight. Which card should I use to maximize points?"
            )
            st.rerun()

        if st.button("📅 Q1 Categories", help="Check quarterly rotating categories"):
            click_suggestion(
                "What are the Chase Freedom quarterly categories for Q1 2026?"
            )
            st.rerun()

    with col2:
        if st.button("✈️ Travel Bank Trick", help="Learn how to use airline credits"):
            click_suggestion(
                "How can I use my Amex Platinum airline incidental credit with United Travel Bank?"
            )
            st.rerun()

        if st.button("🔍 Chase 5/24 Rule", help="Explain the famous application rule"):
            click_suggestion(
                "Explain the Chase 5/24 rule and check if I am affected based on my cards."
            )
            st.rerun()

# --- 🌟 功能 2: 渲染历史聊天记录 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 🌟 功能 3: 处理用户输入 ---
# 3.1 底部输入框
if prompt := st.chat_input("E.g., Which card for groceries?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()  # 强制刷新，以便立即显示用户的输入

# 3.2 触发 AI 回复 (核心逻辑：只要最后一条是 User，就生成回答)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.status("Thinking...", expanded=False) as status:
            # 获取上下文
            history = st.session_state.messages[:-1]
            last_msg = st.session_state.messages[-1]["content"]

            # 调用 Gemini
            response = generate_response_with_retry(last_msg, history)

            status.update(label="Done", state="complete")

        st.markdown(response)

    # 将 AI 回复存入历史
    st.session_state.messages.append({"role": "assistant", "content": response})
