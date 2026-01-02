import os
import sys

# 将 src 目录添加到路径，以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import Benefit, CreditCard, UserProfile


def test_create_profile():
    # 1. 创建用户
    user = UserProfile(user_id="walle_owner")

    # 2. 模拟添加一张 Amex Platinum
    amex_plat = CreditCard(
        bank="Amex", name="Platinum", network="Amex", last_four="1001"
    )

    # 添加福利
    uber_cash = Benefit(
        name="Uber Cash",
        category="transport",
        description="$15 monthly Uber credit",
        refresh_period="monthly",
        total_amount=15.0,
    )

    saks_credit = Benefit(
        name="Saks Credit",
        category="shopping",
        description="$50 semi-annual Saks credit",
        refresh_period="semi-annual",
        total_amount=50.0,
    )

    amex_plat.add_benefit(uber_cash)
    amex_plat.add_benefit(saks_credit)

    user.add_card(amex_plat)

    # 3. 打印结果
    print("=== JSON Output for LLM ===")
    print(user.to_json())

    print("\n=== System Prompt Summary ===")
    print(user.get_summary())


if __name__ == "__main__":
    test_create_profile()
