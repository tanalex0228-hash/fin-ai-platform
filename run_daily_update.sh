#!/bin/bash

# 專案根目錄
PROJECT_DIR="/Users/apple/Desktop/fin_ai_platform"

# venv 的 python
PYTHON="$PROJECT_DIR/venv/bin/python"

# log 檔
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "===== $(date) START daily price update =====" >> "$LOG_DIR/daily_update.log"

cd "$PROJECT_DIR" || exit 1

$PYTHON load_prices.py >> "$LOG_DIR/daily_update.log" 2>&1

echo "===== $(date) END daily price update =====" >> "$LOG_DIR/daily_update.log"


