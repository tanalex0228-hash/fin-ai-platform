# app/services/stock_summary_service.py
# -------------------------------------
# ⭐ 整合：技術面 + 基本面（A2）+ 風險面 → 前端 stock_detail.html 使用

from app.services.data_technical_service import calc_latest_technical
from app.services.fundamental_service import calc_fundamental_factors   # ← 修正 import
from app.services.risk_service import calc_risk_factors
from app.services.risk_score_service import (
    score_vol, score_mdd, score_turnover, score_trend_risk, combine_risk_scores
)


def get_stock_summary(symbol):

    # ============= 技術面 =============
    technical = calc_latest_technical(symbol)
    tech_score = technical.get("score", 0)

    # ============= 基本面（新版 A2） =============
    fundamental = calc_fundamental_factors(symbol)
    fund_score = fundamental.get("a2_score") or 0

    # ============= 風險面 =============
    raw_risk = calc_risk_factors(symbol)

    if raw_risk:
        risk_scores = {
            "vol": score_vol(raw_risk.get("volatility")),
            "mdd": score_mdd(raw_risk.get("max_drawdown")),
            "liq": score_turnover(raw_risk.get("turnover")),
            "trend": score_trend_risk(raw_risk.get("trend_risk")),
        }
        risk_final = combine_risk_scores(risk_scores)

        risk_report = (
            f"波動 {raw_risk.get('volatility')}%, "
            f"MDD {raw_risk.get('max_drawdown')}%, "
            f"成交額 {raw_risk.get('turnover')}"
        )
    else:
        risk_scores = {}
        risk_final = None
        risk_report = "無風險資料"

    # ============= 綜合總分（技術 + 基本面） =============
    final_score = tech_score + fund_score   # 0~200

    # ============= 等級 =============
    def grade(x):
        if x is None: return "N/A"
        if x >= 180: return "A+"
        if x >= 160: return "A"
        if x >= 140: return "B"
        if x >= 120: return "C"
        if x >= 100: return "D"
        return "E"

    grade_final = grade(final_score)

    # ============= 回傳格式（前端 HTML 使用） =============
    return {
        "symbol": symbol,
        "date": technical.get("latest", {}).get("date"),

        "technical": technical,

        "fundamental": {
            "metrics": fundamental["metrics"],
            "scores": fundamental["scores"],              # ✔ 給雷達圖用
            "final_weights": fundamental["final_weights"],
            "a2_score": fundamental["a2_score"],
            "a2_grade": fundamental["a2_grade"],
        },

        "risk": {
            "raw": raw_risk,
            "scores": risk_scores,
            "final": risk_final,
            "report": risk_report,
        },

        "score_final": final_score,
        "grade_final": grade_final,
    }
