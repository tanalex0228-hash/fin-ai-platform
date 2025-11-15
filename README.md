fin-ai-platform



A backend financial data platform
Built to fetch, store, analyze and serve stock market data through a clean API for future analytical and trading applications.



📌 專案目標（Project Vision）
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



🏗 系統架構（Architecture）
┌──────────────────────────┐
│          Frontend        │
│ (HTML / JavaScript /     │
│  React - planned)        │
└───────────────▲─────────┘
                │ REST API (JSON)
┌───────────────┴─────────┐
│        Flask Backend     │
│  /api/fetch_prices       │
│  /api/get_prices         │
│  /api/health             │
└───────────────▲─────────┘
                │ Writes / Reads
┌───────────────┴─────────┐
│        Database Layer     │
│   MySQL (production)      │
│   SQLite (local dev)      │
│ prices(symbol, date, ...) │
└──────────────────────────┘



🔧 使用技術（Tech Stack）
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



🗄 資料庫 Schema
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
🚀 API Endpoints
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



📈 開發進度（Progress）
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



🧭 Roadmap（未來計畫）
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


     
🚀 （2）開發架構（Development Architecture）
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



🚀 （3）邏輯架構（Logical Flow Architecture）
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



🚀 （4）計算架構（Computation Architecture）
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



🚀 （5） 62 項功能（整理成架構樹）
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
🚀 （6）股票評估的技術策略說明
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



👨‍💻 開發者
Alex Tan
Finance & International Business
Building a fintech backend from scratch.# fin-ai-platform
