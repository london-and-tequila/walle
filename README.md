# 🤖 Walle: AI Credit Card Maximizer

> "Not just a chatbot, but a persistent AI Agent for your personal finance."

**Walle** 是一个基于 **Google Gemini** 构建的智能信用卡管理 Agent。它不仅能通过逻辑推理帮你计算每一笔消费的最佳刷卡策略，还拥有**云端记忆**，能够永久保存你的持卡组合，随时随地为你提供个性化的金融建议。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)
![Database](https://img.shields.io/badge/Storage-Google%20Sheets-green.svg)

---

## ✨ 核心功能 (Key Features)

### 🧠 1. 强力 AI 大脑
* 集成 **Google Gemini 1.5 Pro / Flash** 模型。
* 具备**复杂逻辑推理**能力：自动计算倍率叠加（例如：Chase Freedom 季度 5% + 餐饮 3% = 7%）。
* **联网搜索**: 集成 Tavily API，实时查询最新的季度轮换类别 (Quarterly Categories) 和银行政策。

### 💾 2. 云端持久化记忆 (New!)
* **Google Sheets Database**: 使用 Google Sheets 作为云数据库。
* **多端同步**: 无论在本地、手机还是云端部署，你的持卡数据永远同步，不会因刷新页面而丢失。

### 🎨 3. 现代化 Web 交互
* **Streamlit UI**: 采用 "Premium Fintech" 设计风格（深海蓝 + 金色）。
* **交互式管理**: 侧边栏支持动态添加/删除卡片，支持自动推断发卡组织（Network）。
* **智能抗压**: 内置 API 限流重试机制 (Retry with Backoff)，彻底告别 `429 Too Many Requests`。

---

## 🛠️ 技术栈 (Tech Stack)

* **LLM Framework**: `google-genai` (Official SDK)
* **Frontend**: Streamlit + Custom CSS
* **Search Tool**: Tavily Search API
* **Database**: Google Sheets API (`gspread`)
* **Auth**: Google Cloud Service Account

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保安装 Python 3.10+。

```bash
git clone [https://github.com/your-username/walle.git](https://github.com/your-username/walle.git)
cd walle
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt