import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class Benefit:
    """定义单个信用卡福利 (例如: $10 Uber Cash, 5% Grocery)"""

    name: str  # 福利名称, e.g., "Uber Cash"
    category: str  # 类别, e.g., "travel", "dining", "shopping"
    description: str  # 描述
    refresh_period: str  # 刷新周期, e.g., "monthly", "quarterly", "annual"
    total_amount: float = 0.0  # 总额度, e.g., 10.0
    used_amount: float = 0.0  # 已用额度 (难点数据，初期可能默认为0)

    @property
    def remaining_amount(self) -> float:
        return max(0.0, self.total_amount - self.used_amount)


@dataclass
class CreditCard:
    """定义一张信用卡"""

    bank: str  # e.g., "Amex", "Chase"
    name: str  # e.g., "Platinum", "Freedom Flex"
    network: str  # e.g., "Visa", "Amex"
    last_four: str = "0000"  # 卡号后四位，用于区分
    benefits: List[Benefit] = field(default_factory=list)
    open_date: str = ""

    def add_benefit(self, benefit: Benefit):
        self.benefits.append(benefit)

    def __str__(self):
        return f"{self.bank} {self.name} ({self.last_four})"


@dataclass
class UserProfile:
    """定义用户画像"""

    user_id: str
    cards: List[CreditCard] = field(default_factory=list)

    def add_card(self, card: CreditCard):
        self.cards.append(card)

    def to_json(self):
        """序列化为 JSON，方便传递给 Gemini"""
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    def get_summary(self) -> str:
        """生成一段给 LLM 看的 System Prompt 摘要"""
        summary = [f"User holds {len(self.cards)} cards:"]
        for card in self.cards:
            summary.append(f"- {card.bank} {card.name}")
            for ben in card.benefits:
                summary.append(
                    f"  * [Benefit] {ben.name}: ${ben.remaining_amount} left ({ben.refresh_period})"
                )
        return "\n".join(summary)
