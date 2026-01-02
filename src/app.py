import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 路径配置 (必须在 import src 之前) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import CreditCard
from src.storage import (
    delete_card_from_db,
    load_user_data,
    save_new_card,
    update_card_in_db,
)
from src.tools.search import search_credit_card_info

# --- 1. 国际化字典 (Translation Dictionary) ---
TRANSLATIONS = {
    "en": {
        "page_title": "Walle: Credit Card Agent",
        "page_caption": "Maximize rewards, track benefits, and master your wallet.",
        "login_title": "🤖 Walle Login",
        "login_prompt": "Please enter your email to access your wallet.",
        "email_placeholder": "e.g. tony@stark.com",
        "login_btn": "🚀 Login / Register",
        "welcome": "Welcome, {user}!",
        "user_label": "👤 User: {user}",
        "logout_btn": "Logout",
        "sidebar_title": "🤖 Walle Brain",
        "wallet_header": "💳 Your Wallet",
        "no_cards": "No cards yet. Add one below!",
        "add_card_expander": "➕ Add New Card",
        "bank_label": "Bank",
        "card_name_label": "Card Name",
        "network_label": "Network",
        "last4_label": "Last 4",
        "opendate_label": "Open Date",
        "add_btn": "Add to Wallet",
        "added_msg": "Added {card}!",
        "missing_info": "Please fill in Bank and Card Name.",
        "reset_btn": "🔄 Reset Demo",
        "edit_save": "💾 Save",
        "edit_updated": "Updated!",
        "edit_mode_toggle": "✏️ Edit Mode",  # Legacy (if needed)
        "btn_edit": "✏️ Edit",
        "btn_del": "🗑️ Del",
        "hero_title": "👋 How can I help you today?",
        "hero_subtitle": "Here are a few things I can do for you:",
        "hero_btn_dining": "🍔 Dining Spending",
        "hero_query_dining": "I'm going out for dinner tonight. Which card should I use to maximize points?",
        "hero_btn_q1": "📅 Q1 Categories",
        "hero_query_q1": "What are the Chase Freedom quarterly categories for Q1 2026?",
        "hero_btn_travel": "✈️ Travel Bank Trick",
        "hero_query_travel": "How can I use my Amex Platinum airline incidental credit with United Travel Bank?",
        "hero_btn_524": "🔍 Chase 5/24 Rule",
        "hero_query_524": "Explain the Chase 5/24 rule and check if I am affected based on my cards.",
        "chat_placeholder": "E.g., Which card for groceries?",
        "thinking": "Thinking...",
        "done": "Done",
        "login_required_title": "Welcome to Walle AI 🤖",
        "login_required_msg": "Your personal credit card maximizer agent.\n\n👈 **Please login using your email in the sidebar to start.**\n\n*(Data is securely stored in your private Google Sheet)*",
    },
    "zh": {
        "page_title": "Walle: 您的玩卡助手",
        "page_caption": "最大化信用卡返现，追踪福利，管理您的卡包。",
        "login_title": "🤖 Walle 登录",
        "login_prompt": "请输入邮箱以访问您的卡包。",
        "email_placeholder": "例如：tony@stark.com",
        "login_btn": "🚀 登录 / 注册",
        "welcome": "欢迎, {user}!",
        "user_label": "👤 用户: {user}",
        "logout_btn": "退出登录",
        "sidebar_title": "🤖 Walle 大脑",
        "wallet_header": "💳 我的卡包",
        "no_cards": "暂无卡片，请在下方添加！",
        "add_card_expander": "➕ 添加新卡",
        "bank_label": "银行",
        "card_name_label": "卡片名称",
        "network_label": "卡组织",
        "last4_label": "尾号",
        "opendate_label": "开卡日期",
        "add_btn": "添加到卡包",
        "added_msg": "已添加 {card}!",
        "missing_info": "请填写银行和卡片名称。",
        "reset_btn": "🔄 重置演示数据",
        "edit_save": "💾 保存修改",
        "edit_updated": "更新成功！",
        "edit_mode_toggle": "✏️ 编辑模式",
        "btn_edit": "✏️ 编辑",
        "btn_del": "🗑️ 删除",
        "hero_title": "👋 今天想问点什么？",
        "hero_subtitle": "我可以帮您解决这些问题：",
        "hero_btn_dining": "🍔 吃饭刷哪张？",
        "hero_query_dining": "我今晚要出去吃饭，刷哪张卡返现最高？",
        "hero_btn_q1": "📅 Q1 季度类别",
        "hero_query_q1": "2026年第一季度 Chase Freedom 的 5% 类别是什么？",
        "hero_btn_travel": "✈️ 航空报销路子",
        "hero_query_travel": "怎么用 UA Travel Bank 把 Amex 白金卡的航空报销撸满？",
        "hero_btn_524": "🔍 Chase 5/24 规则",
        "hero_query_524": "解释一下 Chase 5/24 规则，并根据我的持卡情况看看我受限制了吗。",
        "chat_placeholder": "例如：买菜刷哪张卡？",
        "thinking": "思考中...",
        "done": "完成",
        "login_required_title": "欢迎来到 Walle AI 🤖",
        "login_required_msg": "您的个人信用卡智能助手。\n\n👈 **请在左侧侧边栏输入邮箱登录以开始。**\n\n*(数据安全地存储在您的私人 Google Sheet 中)*",
    },
}

st.set_page_config(
    page_title="Walle AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS 样式 (保持不变) ---
st.markdown(
    """
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .stChatMessage { background-color: #1E2329; border-radius: 15px; padding: 10px; margin-bottom: 10px; border: 1px solid #30363D; }
    .stButton button { border-radius: 20px; font-weight: bold; transition: all 0.3s ease; }
    .stButton button:hover { transform: scale(1.02); }
    [data-testid="stSidebar"] h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; background: -webkit-linear-gradient(45deg, #FFC107, #FF8F00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""",
    unsafe_allow_html=True,
)

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# --- 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_edit_index" not in st.session_state:
    st.session_state.active_edit_index = None
if "language" not in st.session_state:
    st.session_state.language = "en"  # 默认英语


# --- 辅助函数：获取翻译 ---
def t(key, **kwargs):
    lang = st.session_state.language
    text = TRANSLATIONS[lang].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


# --- 辅助函数：图标 ---
def get_network_icon(network):
    icons = {
        "Visa": "💳",
        "Mastercard": "🟠",
        "Amex": "🦅",
        "Discover": "🔭",
        "Unknown": "❓",
    }
    return icons.get(network, "❓")


# --- 数据预设 (保持不变) ---
POPULAR_CARDS = {
    "Chase": [
        "Sapphire Preferred",
        "Sapphire Reserve",
        "Freedom Flex",
        "Freedom Unlimited",
        "Ink Business Preferred",
    ],
    "Amex": ["Platinum", "Gold", "Green", "Blue Cash Preferred", "Delta SkyMiles Gold"],
    "Citi": ["Premier", "Double Cash", "Custom Cash"],
    "Capital One": ["Venture X", "SavorOne"],
    "Discover": ["It Cash Back"],
    "Bilt": ["Bilt Mastercard"],
    "Other": [],
}


# --- 1. 登录逻辑 (Sidebar) ---
def render_login_sidebar():
    with st.sidebar:
        st.title(t("login_title"))

        if "user_id" not in st.session_state:
            st.info(t("login_prompt"))
            with st.form("login_form"):
                email_input = st.text_input("Email", placeholder=t("email_placeholder"))
                if st.form_submit_button(t("login_btn")):
                    if email_input:
                        user_id = email_input.strip().lower()
                        st.session_state.user_id = user_id
                        st.success(t("welcome", user=user_id))
                        time.sleep(0.5)
                        st.rerun()
            return None
        else:
            current_user = st.session_state.user_id
            st.success(t("user_label", user=current_user))
            if st.button(t("logout_btn"), type="secondary"):
                del st.session_state.user_id
                if "user_profile" in st.session_state:
                    del st.session_state.user_profile
                st.rerun()
            return current_user


# --- 获取用户 ID ---
CURRENT_USER_ID = render_login_sidebar()

# --- 登录拦截 ---
if not CURRENT_USER_ID:
    # 顶部添加语言切换 (即使未登录也显示)
    col_t, col_l = st.columns([8, 2])
    with col_t:
        st.title(t("login_required_title"))
    with col_l:
        # 语言选择器
        lang_choice = st.selectbox(
            "Language / 语言",
            ["English", "中文"],
            index=0 if st.session_state.language == "en" else 1,
            key="lang_selector_login",
        )
        new_lang = "en" if lang_choice == "English" else "zh"
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()

    st.markdown(t("login_required_msg"))
    st.stop()

# ==========================================
# 🚀 已登录逻辑
# ==========================================

# 加载数据
if "user_profile" not in st.session_state:
    with st.spinner("Loading..."):
        st.session_state.user_profile = load_user_data(user_id=CURRENT_USER_ID)

# --- 侧边栏：卡包管理 ---
with st.sidebar:
    st.divider()
    st.header(t("sidebar_title"))

    # === A. My Wallet ===
    st.subheader(t("wallet_header"))
    user = st.session_state.user_profile

    if not user.cards:
        st.info(t("no_cards"))
    else:
        for i, card in enumerate(user.cards):
            icon = get_network_icon(card.network)
            with st.expander(
                f"{icon} {card.bank} {card.name} (...{card.last_four})", expanded=False
            ):
                if st.session_state.active_edit_index == i:
                    # [编辑模式]
                    with st.form(key=f"edit_form_{i}"):
                        new_bank = st.text_input(t("bank_label"), value=card.bank)
                        new_name = st.text_input(t("card_name_label"), value=card.name)
                        c1, c2 = st.columns(2)
                        with c1:
                            nets = ["Unknown", "Visa", "Mastercard", "Amex", "Discover"]
                            curr_idx = (
                                nets.index(card.network) if card.network in nets else 0
                            )
                            new_net = st.selectbox(
                                t("network_label"), nets, index=curr_idx
                            )
                        with c2:
                            new_last4 = st.text_input(
                                t("last4_label"), value=card.last_four, max_chars=4
                            )

                        import datetime

                        default_date = None
                        if card.open_date:
                            try:
                                default_date = datetime.datetime.strptime(
                                    card.open_date, "%Y-%m-%d"
                                ).date()
                            except:
                                pass
                        new_open_date = st.date_input(
                            t("opendate_label"), value=default_date
                        )

                        if st.form_submit_button(t("edit_save")):
                            d_str = (
                                new_open_date.strftime("%Y-%m-%d")
                                if new_open_date
                                else ""
                            )
                            updated = CreditCard(
                                new_bank, new_name, new_net, new_last4, d_str
                            )
                            update_card_in_db(CURRENT_USER_ID, i, updated)
                            user.cards[i] = updated
                            st.session_state.active_edit_index = None
                            st.success(t("edit_updated"))
                            time.sleep(0.5)
                            st.rerun()
                else:
                    # [查看模式]
                    st.write(f"**{t('network_label')}:** {card.network}")
                    st.write(f"**{t('last4_label')}:** {card.last_four}")
                    st.write(
                        f"**{t('opendate_label')}:** {card.open_date if card.open_date else 'N/A'}"
                    )
                    ce, cd = st.columns([1, 1])
                    with ce:
                        if st.button(t("btn_edit"), key=f"btn_edit_{i}"):
                            st.session_state.active_edit_index = i
                            st.rerun()
                    with cd:
                        if st.button(t("btn_del"), key=f"del_{i}"):
                            delete_card_from_db(CURRENT_USER_ID, i)
                            user.cards.pop(i)
                            st.rerun()

    # === B. Add New Card ===
    st.divider()
    with st.expander(t("add_card_expander"), expanded=False):
        b_opts = list(POPULAR_CARDS.keys())
        s_bank = st.selectbox(t("bank_label"), b_opts)
        f_bank = st.text_input("Enter Bank") if s_bank == "Other" else s_bank

        c_list = POPULAR_CARDS.get(s_bank, []) + ["Other"]
        s_card = st.selectbox(t("card_name_label"), c_list)
        f_card = st.text_input("Enter Card Name") if s_card == "Other" else s_card

        cn, cl = st.columns(2)
        with cn:
            n_opts = ["Unknown", "Visa", "Mastercard", "Amex", "Discover"]
            idx = 0
            if f_bank == "Amex":
                idx = 3
            elif f_bank == "Discover":
                idx = 4
            elif f_bank == "Bilt":
                idx = 2
            f_net = st.selectbox(t("network_label"), n_opts, index=idx)
        with cl:
            f_last4 = (
                st.text_input(t("last4_label"), max_chars=4, placeholder="8888")
                or "0000"
            )

        f_date = st.date_input(t("opendate_label"), value=None)

        if st.button(t("add_btn"), use_container_width=True):
            if f_bank and f_card:
                d_str = f_date.strftime("%Y-%m-%d") if f_date else ""
                new_c = CreditCard(f_bank, f_card, f_net, f_last4, d_str)
                save_new_card(CURRENT_USER_ID, new_c)
                st.session_state.user_profile.add_card(new_c)
                st.success(t("added_msg", card=f_card))
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(t("missing_info"))

# --- 主界面 Layout ---

# 🌟 使用 columns 实现右上角语言切换
col_main_title, col_main_lang = st.columns([7, 1.5])

with col_main_title:
    st.title(t("page_title"))
    st.caption(t("page_caption"))

with col_main_lang:
    # 语言切换器
    lang_opt = st.selectbox(
        "🌐 Language",
        ["English", "中文"],
        index=0 if st.session_state.language == "en" else 1,
        key="main_lang_select",
        label_visibility="collapsed",
    )  # 隐藏 label 更美观

    # 状态同步
    new_lang_main = "en" if lang_opt == "English" else "zh"
    if new_lang_main != st.session_state.language:
        st.session_state.language = new_lang_main
        st.rerun()


# --- Gemini 逻辑 (保持不变) ---
def get_gemini_client():
    return genai.Client(api_key=api_key)


def generate_response_with_retry(prompt, history):
    client = get_gemini_client()
    user_p = st.session_state.user_profile
    # 提示词稍微加一点语言指示，让 Gemini 尽量用对应语言回答
    lang_instruction = (
        "Respond in English." if st.session_state.language == "en" else "请用中文回答。"
    )

    SYSTEM_INSTRUCTION = f"""
    You are Walle. User Context: {user_p.get_summary()}
    Always SEARCH before answering about categories.
    {lang_instruction}
    """
    tools = [search_credit_card_info]
    contents = [msg["content"] for msg in history]
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=contents,
            config=types.GenerateContentConfig(
                tools=tools, system_instruction=SYSTEM_INSTRUCTION
            ),
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


# --- Hero Section (空状态) ---
if not st.session_state.messages:
    st.markdown(f"### {t('hero_title')}")
    st.markdown(t("hero_subtitle"))

    c1, c2 = st.columns(2)

    def ask(txt):
        st.session_state.messages.append({"role": "user", "content": txt})

    with c1:
        if st.button(t("hero_btn_dining"), use_container_width=True):
            ask(t("hero_query_dining"))
            st.rerun()
        if st.button(t("hero_btn_q1"), use_container_width=True):
            ask(t("hero_query_q1"))
            st.rerun()
    with c2:
        if st.button(t("hero_btn_travel"), use_container_width=True):
            ask(t("hero_query_travel"))
            st.rerun()
        if st.button(t("hero_btn_524"), use_container_width=True):
            ask(t("hero_query_524"))
            st.rerun()

# --- 聊天记录 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 输入框 ---
if prompt := st.chat_input(t("chat_placeholder")):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.status(t("thinking"), expanded=False) as status:
            hist = st.session_state.messages[:-1]
            last = st.session_state.messages[-1]["content"]
            resp = generate_response_with_retry(last, hist)
            status.update(label=t("done"), state="complete")
        st.markdown(resp)
    st.session_state.messages.append({"role": "assistant", "content": resp})
