fin-ai-platform



A backend financial data platform
Built to fetch, store, analyze and serve stock market data through a clean API for future analytical and trading applications.



＃專案目標（Project Vision）
fin-ai-platform 的長期目標是打造一個：
可擴充
可部署
可回測
可自動化
可視覺化
的完整 金融數據平台（Financial Data Engine）。
它可以成為未來：
量化交易
HFT 策略原型
技術指標研究
金融選修課程專案
個人投資儀表板
的基礎架構。


 ＃系統架構（Architecture）



┌──────────────────────────┐
│          Frontend        │
│ (HTML / JavaScript /     │
│  Plotly / React - planned)│
└───────────────▲─────────┘
                │ REST API (JSON)
┌───────────────┴─────────┐
│        Flask Backend     │
│  /api/fetch_prices       │
│  /api/get_prices         │
│  /api/get_indicators     │
│  /api/backtest           │
│  /api/fundamental        │ (WIP)
└───────────────▲─────────┘
                │ Writes / Reads
┌───────────────┴─────────┐
│       Database Layer      │
│   SQLite (local dev)      │
│   MySQL (prod)            │
│   Tables:                 │
│     - stock_prices        │
│     - financial_income    │
│     - financial_balance   │
│     - financial_cashflow  │
│     - fundamental_factors │
│     - indicator_snapshot  │
│     - backtest_results    │
└──────────────────────────┘



 ＃使用技術（Tech Stack）
Backend
Flask (REST API)
Python
Pandas / NumPy
Data Source
yfinance （未來加入 requests 爬蟲）
Database
SQLite（local dev）
MySQL（prod / cloud）
Version Control
Git + GitHub
Deployment（規劃中）
Backend → Railway
Database → PlanetScale
Frontend → Vercel
Static Storage → AWS S3（可選）



 ＃資料庫 Schema
TABLE: prices
-----------------------------------------
id (int, PK, auto increment)
symbol (varchar)
date (date)
open (float)
high (float)
low (float)
close (float)
volume (bigint)
-----------------------------------------
Composite Key: (symbol, date) — planned



 ＃API Endpoints
POST /api/fetch_prices
抓取股票資料 → 清洗 → 寫入資料庫。
Request:
{
  "symbols": ["2330.TW", "AAPL"],
  "period": "1mo"
}
Response:
{
  "status": "success",
  "inserted_rows": 48
}
GET /api/get_prices?symbol=2330.TW
回傳資料庫資料。
Response:
{
  "symbol": "2330.TW",
  "data": [...],
  "count": 30
}



 ＃開發進度（Progress）
模組	狀態
抓取多股票資料	✅ 完成
MultiIndex 欄位清洗	🔄 進行中
資料庫寫入	🔄 進行中
查詢 API	🔄 建置中
GitHub 版本管理	✅ 完成
去除 venv / db	🔄 清理中
前端 UI	⏳ 未開始
自動排程	⏳ 未開始
雲端部署	⏳ 未開始



 ＃Roadmap（未來計畫）
Phase 1 — Data Engine
整理 yfinance 欄位
設計資料庫主鍵
基礎 API 完成
Phase 2 — Technical Indicators
MA / EMA
RSI
MACD
BBands
Phase 3 — Backtesting Engine
支援跨股票策略
部位管理
交易紀錄
Phase 4 — Full Deployment
Railway 部署 API
PlanetScale 部署 MySQL
Vercel 部署前端
自動化 ETL（每天抓資料）




-----------------------------------------------





🚀 （1）平台整體架構圖（System Architecture）
                                 ┌──────────────────────────┐
                                 │        FRONTEND          │
                                 │  Web UI / React (future) │
                                 │  Charting / Dashboard    │
                                 └───────────────▲─────────┘
                                                 │ HTTP (JSON)
                                                 │
┌───────────────────────────────┐   ┌───────────┴────────────┐
│  Scheduler / Cron Jobs         │   │        Flask API        │
│ (Daily ETL, Auto Fetch)        │   │  /api/fetch_prices      │
│───────────┬────────────────────│   │  /api/get_prices        │
│ TaskQueue │ Redis / Celery     │   │  /api/indicators        │
└─────▲─────┘                    │   │  /api/backtest          │
      │                          │   └───────────▲────────────┘
      │Triggers (daily)          │               │ Read/Write
      │                          │
┌─────┴──────────────────────────▼────┐
│       Data Processing Layer          │
│  yfinance fetcher / Web crawler      │
│  Data cleaning / MultiIndex flatten  │
│  Indicator Engine (MA, RSI, MACD…)   │
│  Backtest Engine                     │
└───────────────▲──────────────────────┘
                │
                │ Writes / Queries
                │
     ┌──────────┴──────────────────────┐
     │          Database Layer          │
     │  PlanetScale (MySQL Cloud)       │
     │  SQLite (local dev)              │
     │  Tables: prices, indicators,     │
     │          strategies, trades      │
     └──────────────────────────────────┘


     
 ＃（2）開發架構（Development Architecture）
Your Mac (Local Development)
├── Python venv
├── Flask backend
├── SQLite local DB
├── Git (version control)
└── Push → GitHub (main branch)
           ↓
           Cloud Deploy:
           - Backend → Railway
           - DB → PlanetScale
           - UI → Vercel
開發流程：
[本地修改] → [git commit] → [git push] → [CI/CD 自動部署（未來）]



 ＃（3）邏輯架構（Logical Flow Architecture）
User → Frontend → API → Processing → Database → API → Frontend display
更細分：
(1) User Input (symbols / period)
(2) API receives request
(3) Validates input
(4) Calls data fetcher
(5) yfinance / crawler returns raw data
(6) Data cleaning → pandas
(7) Indicators computation（optional）
(8) Insert to database
(9) API returns response



 ＃（4）計算架構（Computation Architecture）
Data Source Layer
  ├─ yfinance API
  └─ Web Scraper (future)

Computation Layer
  ├─ Preprocessing
  │    - Flatten columns
  │    - Normalize date formats
  │    - Remove NaN
  │    - Adjust timezone
  ├─ Feature Layer
  │    - Technical Indicators (MA, EMA, RSI…)
  │    - Financial Scoring Factors
  │    - Risk Measures (Volatility, Sharpe)
  ├─ Backtesting Engine
  │    - Entry/exit rules
  │    - Position sizing
  │    - PnL calculation
  └─ Optimization Layer (future)
       - Grid search
       - Walk-forward analysis
       - Monte Carlo simulation



 ＃（5） 62 項功能（整理成架構樹）
我將你提過的所有功能歸類：
Ⅰ. 股票資料擷取（Data Fetching）
多股票一次抓
自動填補缺漏資料
自訂期間（1d, 1mo, 1y…）
跨市場資料（TW、US、HK）
K 線資料
成交量
歷史股利
現金殖利率
ETF 成分股
財報 API（未來）
Ⅱ. 資料清洗（Data Cleaning）
MultiIndex 換單層欄位
日期格式統一
NaN 去除
數字欄位轉 float
自動去除重複資料
資料完整性檢查
時區統一
Ⅲ. 資料庫功能（Database Layer）
MySQL Schema 設計
主鍵（symbol + date）
批次寫入
避免重複寫入
讀取分頁
排序查詢
資料更新（upsert）
SQLite → MySQL 遷移
Ⅳ. 技術指標（Indicators Engine）
移動平均（MA / EMA）
RSI
MACD
布林通道（BBands）
威廉指標
KD 指標
ATR
OBV
VWAP
Ⅴ. 策略模型（Strategy Engine）
黃金交叉 / 死亡交叉
突破策略
均線乖離策略
RSI 超買超賣
成交量暴增策略
價量背離
波段順勢策略
趨勢反轉策略
Ⅵ. 回測（Backtesting）
Entry / Exit
止盈
止損
部位管理（Position sizing）
資金曲線計算
最大回撤
Sharpe ratio
Win rate
Trade summary
Ⅶ. API 功能
fetch_prices
get_prices
get_indicators
get_backtest
get_health
分頁查詢
symbol 列表
Ⅷ. 前端功能（Future UI）
K 線圖
技術指標顯示
策略模擬介面
資產走勢圖（盈虧曲線）
 ＃（6）股票評估的技術策略說明
我整理成「策略分類系統」＋每種策略的說明。
A. 趨勢追蹤策略（Trend Following）
適合長線、中線
核心思想：抱著順勢，避免逆勢
方法：
MA 長短線交叉（黃金交叉、死亡交叉）
MACD 柱狀體翻正/翻負
價格突破前高/前低
邏輯：
若 MA5 > MA20 → 多頭
若 MA5 < MA20 → 空頭
B. 超買超賣策略（Mean Reversion）
適合短線
核心思想：價格偏離均值後會回到平均
方法：
RSI < 30 → 可能反彈
RSI > 70 → 可能回落
布林通道下緣 → 反彈機率高
C. 價量分析（Volume-Based Strategy）
適合波段交易
核心思想：量先於價
方法：
催量突破 = 趨勢確立
OBV 上升代表買盤強
D. 波動度策略（Volatility Strategy）
適合短線
方法：
ATR 高 → 不適合進場
ATR 低 → 適合突破策略
E. 多因子策略（Multi-Factor Modeling）
適合長期投資
涉及：
價值因子（本益比、淨值比）
成長因子（EPS、營收）
動能因子（12 個月收益）
風險因子（Beta、波動度）
F. 量化回測流程（Backtest Logic）
for each bar:
    check entry
    if in position:
        update stop loss/take profit
        check exit
    update portfolio value
結果包含：
勝率
年化報酬
最大回撤
夏普值
交易筆數







⸻

🧱 fin-ai-platform

A backend-driven financial data & quant analysis platform
Built to fetch, store, analyze, visualize, and backtest stock market data through a clean API.
Designed for future:
	•	Quantitative research
	•	Technical indicator engines
	•	Fundamental factor modeling
	•	Strategy backtesting
	•	Automated trading pipelines
	•	Personal investment dashboards

⸻

🔧 使用技術（Tech Stack）

Backend
	•	Flask REST API
	•	Python
	•	Pandas / NumPy
	•	Technical indicator engine

Database
	•	SQLite（local dev）
	•	MySQL（production, planned）

Data Source
	•	yfinance（股價）
	•	FinMind API（財報 → 安全、整理後、非爬蟲）
	•	未來加入 TWSE/MOPS backup pipeline（避免缺漏）

Version Control
	•	Git / GitHub

Deployment（規劃中）
	•	Backend → Railway
	•	DB → PlanetScale
	•	Frontend → Vercel
	•	Static storage → AWS S3

⸻

🗄 資料庫 Schema（完整）

🔹 stock_prices

（你原本的版本 + 你目前真實資料）

id (PK)
stock_id (varchar)
date (date)
open (float)
high (float)
low (float)
close (float)
volume (bigint)

約共 1,410,487+ 筆資料




🔹 financial_income_statement（FinMind）

stock_id
date
revenue
gross_profit
operating_income
net_income
eps



🔹 financial_balance_sheet（FinMind）

stock_id
date
total_assets
total_liabilities
shareholders_equity
current_assets
current_liabilities



🔹 financial_cashflow（FinMind）

stock_id
date
operating_cashflow
investing_cashflow
financing_cashflow
free_cashflow



🔹 fundamental_factors（WIP）

（A2 基本面評分）
	•	ROE
	•	ROA
	•	毛利率
	•	營益率
	•	EPS YoY
	•	Revenue YoY
	•	Risk Factor Score

🔹 indicator_snapshot（optional）

儲存技術面快照。

🔹 backtest_results（已完成）
	•	parameters
	•	trades
	•	cum_strategy
	•	cum_buy_hold
	•	drawdown
	•	equity_curve

⸻

📡 API Endpoints

✔ 1. Fetch prices

POST /api/fetch_prices

✔ 2. Get prices

GET /api/get_prices?symbol=2330.TW

✔ 3. Technical Indicators

（後端已具備 MA/MACD/RSI/KD/BB）

GET /api/get_indicators?symbol=2330.TW

✔ 4. Backtest Engine

POST /api/backtest

回傳：
	•	策略績效
	•	技術指標
	•	交易紀錄
	•	最大回撤

⸻

📈 功能（整合 62 項完整版）

（完全保留＋整合你之前寫的 62 項功能樹）

✔ 股票資料擷取
✔ 資料清洗
✔ 技術指標
✔ 交易策略模型
✔ 回測引擎（你現在已完成）
✔ 財報資料（FinMind）
✔ 基本面評分（A2 系統）
✔ 自動抓資料（tw_top500）
✔ 雷達圖視覺化
✔ 利潤曲線（equity curve）
✔ K 線圖 + MA / MACD / RSI 可視化

⸻

📊 前端圖表

使用 Plotly：
	•	K 線（蠟燭圖）
	•	均線
	•	MACD
	•	RSI
	•	KD
	•	雷達圖（技術+基本面）
	•	回測績效曲線

⸻

🧭 Roadmap（整合舊版 + 你現在的進度）

Phase 1 — Data Engine ✔（完成）
	•	yfinance 抓取
	•	DB 儲存
	•	基本清洗

Phase 2 — Technical Indicators ✔ 80%
	•	MA, MACD, RSI, BB 完成
	•	KD 修正中（已修好）

Phase 3 — Fundamental Engine ✔ 70%
	•	FinMind 三大表完成
	•	基本面 A2 因子計算（WIP）

Phase 4 — Backtesting Engine ✔（完成）
	•	Trend filter
	•	MACD / RSI rules
	•	Equity curve
	•	Drawdown

Phase 5 — Deployment（未開始）
	•	Railway API
	•	Vercel 前端
	•	Cron job





 ＃ 開發者
Alex Tan
Finance & International Business
Building a fintech backend from scratch.# fin-ai-platform



