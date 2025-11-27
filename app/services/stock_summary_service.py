# app/services/stock_summary_service.py

from app.services.data_technical_service import calc_latest_technical
from app.services.data_fundamental_service import calc_fundamental_factors
from app.services.risk_service import calc_risk_factors
from app.services.risk_score_service import (
    score_vol, score_mdd, score_turnover, combine_risk_scores
)


def get_stock_summary(symbol):

    # ============= 技術面 =============
    technical = calc_latest_technical(symbol)

    # ============= 基本面 =============
    fundamental = calc_fundamental_factors(symbol)

    # ============= 風險面 =============
    risk_raw = calc_risk_factors(symbol)

    if risk_raw:
        risk_scores = {
            "vol": score_vol(risk_raw.get("vol")),
            "mdd": score_mdd(risk_raw.get("mdd")),
            "liq": score_turnover(risk_raw.get("turnover")),
        }
        risk_final = combine_risk_scores(risk_scores)
    else:
        risk_scores = {}
        risk_final = None

    # ============= 綜合總分（技術 100 + 基本面 100） =============
    tech_score = technical.get("score", 0)
    fund_score = fundamental.get("a2_score", 0)
    final_score = tech_score + (fund_score or 0)

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

    # ============= 回傳給前端 =============
    return {
        "symbol": symbol,
        "date": technical.get("latest", {}).get("date", None),
        "technical": technical,
        "fundamental": fundamental,
        "risk": {
            "raw": risk_raw,
            "scores": risk_scores,
            "final": risk_final,
            "report": f"波動 {risk_raw.get('vol')}%, MDD {risk_raw.get('mdd')}%, turnover {risk_raw.get('turnover')}"
        },
        "score_final": final_score,
        "grade_final": grade_final,
    }
