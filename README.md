# Walle (Wallet-E) 🤖💳

> **"Your Personal Credit Card Benefit Maximizer."**
> Walle 不捡垃圾，Walle 帮你捡回那些被遗忘的信用卡福利和羊毛。

Walle 是一个基于 **Google Gemini** 构建的开源 AI Agent。它的目标非常简单：作为你的智能钱包管家，帮你理清复杂的信用卡条款，确保你不再错过任何一个 $10 的报销，也不错过任何一次 5% 的返现机会。

## 🎯 核心功能 (Core Features)

* **🧠 智能感知**: 知道你持有谁家的卡 (Amex, Chase, Citi...)。
* **📅 动态日历**: 自动追踪并提醒你季度轮换类别 (如 Chase Freedom, Discover It)。
* **💰 报销猎手**: 监控年度/月度报销额度 (Uber Cash, Dining Credit, Travel Bank)，在过期前发出预警。
* **🌐 实时联网**: 通过搜索工具 (Search Tool) 实时获取最新的福利变化和论坛 (如 Reddit, DoC) 的最新玩法。

## 🛠 技术栈 (Tech Stack)

* **Core Brain**: Google Gemini 1.5 Pro/Flash
* **Framework**: Python (Native / LangChain 待定)
* **Tools**: Google Search API, Custom Scrapers
* **Interface**: CLI (当前) -> Web UI (计划中)

## 🚀 快速开始 (Getting Started)

1. **Clone repo**
   ```bash
   git clone [https://github.com/yourusername/walle.git](https://github.com/yourusername/walle.git)
   cd walle