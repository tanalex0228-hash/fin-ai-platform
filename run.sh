#!/bin/bash

# === 1. 進入專案根目錄 ===
cd "$(dirname "$0")"

# === 2. 啟動虛擬環境 ===
source venv/bin/activate

# === 3. 顯示友善提示 ===
echo ""
echo "🚀 虛擬環境已啟動 (venv)"
echo "📁 目前位置：$(pwd)"
echo ""

# === 4. 模式選擇 ===
echo "請選擇模式："
echo "1 = 啟動 Flask 伺服器"
echo "2 = 生成台股熱門 500 清單 (tw_top500.json)"
echo "3 = 抓台股資料寫入 DB（使用 tw_top500.json）"
echo "4 = 執行任意 Python 腳本"
echo "5 = 執行每日更新（load_prices.py）"
echo "q = 離開"
echo ""
read -p "輸入選項：" mode

# === 5. 行為 ===
case "$mode" in

1)
    echo "🔥 啟動 Flask..."
    python run.py
    ;;

2)
    echo "🔥 生成台股熱門 500 清單..."
    python fetch_tw_top500.py
    ;;

3)
    echo "🔥 用 tw_top500.json 抓資料寫入 DB..."
    python - << 'EOF'
import subprocess, json, os

with open("tw_top500.json", "r") as f:
    symbols = json.load(f)

cmd = [
    "curl", "-X", "POST",
    "http://127.0.0.1:5000/api/fetch_prices",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"symbols": symbols, "period": "10y"})
]

print("📡 正在抓取資料寫入 DB...")
subprocess.run(cmd)
EOF
    ;;

4)
    read -p "輸入 Python 檔名（例如 test.py）：" file
    echo "🔥 執行 $file ..."
    python "$file"
    ;;

5)
    echo "🔥 執行每日更新（load_prices.py）..."
    python load_prices.py
    ;;

q)
    echo "👋 Bye"
    exit 0
    ;;

*)
    echo "❌ 無效選項。"
    ;;
esac
