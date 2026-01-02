import logging
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TavilySearchTool:
    # 🌟 定义核心信源白名单 (中英混合)
    TRUSTED_DOMAINS = [
        "doctorofcredit.com",  # 英文：最快的新闻和羊毛
        "uscreditcardguide.com",  # 中文：美卡指南 (攻略)
        "uscardforum.com",  # 中文：美卡论坛 (DP/讨论)
        "thepointsguy.com",  # 英文：主流评测
        "reddit.com",  # 英文：r/churning
        "frequentmiler.com",  # 英文：深度分析
    ]

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("❌ TAVILY_API_KEY is missing in .env file")

        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str) -> str:
        logger.info(f"🔍 Searching with Tavily (Trusted Sources): {query}")

        try:
            # 💡 技巧：如果用户用中文提问，Tavily 在中文站点的搜索效果会更好
            # 我们通过 include_domains 强行让它关注这些特定网站
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=5,  # 稍微增加结果数，因为现在源变多了
                include_answer=True,
                include_domains=self.TRUSTED_DOMAINS,  # 👈 关键修改：只搜这些高质量站点
            )

            results_context = "Search Results from Trusted Community (USCreditCardGuide/DoC/Reddit):\n\n"

            if response.get("answer"):
                results_context += f"Direct Answer: {response['answer']}\n\n"

            for res in response.get("results", []):
                title = res.get("title", "No Title")
                url = res.get("url", "")
                content = res.get("content", "")

                # 简单的标记，让 Agent 知道这是中文源还是英文源
                source_tag = "[CN]" if "uscard" in url or "guide" in url else "[EN]"

                results_context += f"--- Source {source_tag}: [{title}]({url}) ---\n"
                results_context += f"Content: {content}\n\n"

            return results_context

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return f"Error searching web: {str(e)}"


# 下面的 search_credit_card_info 函数保持不变...
def search_credit_card_info(query: str):
    """
    Use this tool to search for real-time credit card benefits, quarterly categories,
    and latest data points.

    IMPORTANT: This tool searches both English sources (Doctor of Credit, Reddit)
    and Chinese sources (USCreditCardGuide, USCardForum).
    For best results, you can use mixed English/Chinese queries like "Amex Airline Credit 报销".

    Args:
        query: The search query string.
    """
    tool = TavilySearchTool()
    return tool.search(query)
