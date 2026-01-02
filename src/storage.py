import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from src.models import CreditCard, UserProfile

# 定义权限范围
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_db_connection():
    """
    连接到 Google Sheets (带缓存，避免每次刷新都重新连接)
    """
    try:
        # 1. 将 secrets 转换为普通字典 (Streamlit secrets 有时是特殊对象)
        credentials_dict = dict(st.secrets["gcp_service_account"])

        # 2. 🚑 关键修复：处理 private_key 中的换行符
        # TOML 读取出来的 \n 有时是字符串字面量，需要转义为真正的换行符
        if "private_key" in credentials_dict:
            credentials_dict["private_key"] = credentials_dict["private_key"].replace(
                "\\n", "\n"
            )

        # 创建认证凭证
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

        # 授权并打开表格
        client = gspread.authorize(creds)

        # 打开表格
        sheet = client.open("walle_database").worksheet("Cards")
        return sheet

    except Exception as e:
        # 打印更详细的错误堆栈，方便调试
        import traceback

        st.error(f"❌ Database Connection Error: {e}")
        st.code(traceback.format_exc())  # 这行能让你看到具体的报错位置
        return None


def load_user_data(user_id="owner_001"):
    """
    从表格读取数据，并转换为 UserProfile 对象
    """
    sheet = get_db_connection()
    if not sheet:
        return UserProfile(user_id)

    # 读取所有记录 (返回 list of dicts)
    records = sheet.get_all_records()

    user = UserProfile(user_id=user_id)

    # 过滤出当前用户的数据
    for row in records:
        if row.get("user_id") == user_id:
            # 重建 CreditCard 对象
            card = CreditCard(
                bank=str(row["bank"]),
                name=str(row["card_name"]),
                network=str(row["network"]),
                last_four=str(row["last_four"]),
                open_date=str(row.get("open_date", "")),
            )
            # 注意：Benefit 这里暂时留空，或者让 AI 在运行时推理
            # 如果你想存 Benefit，需要在表格加更多列，目前 V1 保持简单
            user.add_card(card)

    return user


def save_new_card(user_id, card: CreditCard):
    """
    向表格追加一行新卡片
    """
    sheet = get_db_connection()
    if sheet:
        # 构造一行数据 [user_id, bank, card_name, network, last_four]
        row_data = [
            user_id,
            card.bank,
            card.name,
            card.network,
            card.last_four,
            card.open_date,
        ]
        sheet.append_row(row_data)


def delete_card_from_db(user_id, card_index):
    """
    从表格删除卡片
    注意：这比较 tricky，我们假设表格里的顺序和 UI 顺序一致。
    """
    sheet = get_db_connection()
    if sheet:
        # 获取所有数据以找到对应的行号
        # 表头是第1行，数据从第2行开始
        # 这是一个简单的实现，假设 owner_001 的数据是连续的
        # 为了生产环境稳健性，通常需要唯一的 card_id，但在 V1 我们用简单逻辑

        all_values = sheet.get_all_values()  # 包含表头

        current_user_rows = []
        for i, row in enumerate(all_values):
            if i == 0:
                continue  # 跳过表头
            if row[0] == user_id:  # row[0] 是 user_id 列
                current_user_rows.append(i + 1)  # 记录真实的行号 (1-based)

        if card_index < len(current_user_rows):
            row_to_delete = current_user_rows[card_index]
            sheet.delete_rows(row_to_delete)
