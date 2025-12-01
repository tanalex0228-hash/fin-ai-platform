# app/services/fundamental_scoring.py

import math


# ======================================================
# 基本 7 因子 Scoring Functions
# ======================================================

def score_pe(x):
    if x is None or x <= 0:
        return 0
    if x < 10:   return 100
    if x < 20:   return 80
    if x < 30:   return 60
    if x < 40:   return 40
    return 20


def score_pb(x):
    if x is None or x <= 0:
        return 0
    if x < 1:   return 100
    if x < 2:   return 80
    if x < 3:   return 60
    if x < 4:   return 40
    return 20


def score_ps(x):
    if x is None or x <= 0:
        return 0
    if x < 1:   return 100
    if x < 2:   return 80
    if x < 3:   return 60
    if x < 5:   return 40
    return 20


def score_roe(x):
    if x is None: 
        return 0
    x *= 100
    if x >= 20: return 100
    if x >= 15: return 90
    if x >= 10: return 75
    if x >= 5:  return 60
    if x >= 0:  return 40
    return 10


def score_roa(x):
    if x is None: 
        return 0
    x *= 100
    if x >= 10: return 100
    if x >= 7:  return 90
    if x >= 5:  return 75
    if x >= 3:  return 60
    if x >= 0:  return 40
    return 10


def score_revenue(x):
    if x is None:
        return 0
    try:
        s = math.log10(max(x, 1))
    except:
        return 0
    s_norm = (s - 5) / (9 - 5)
    return max(0, min(100, int(s_norm * 100)))


def score_eps(x):
    if x is None:
        return 0
    if x >= 10: return 100
    if x >= 5:  return 90
    if x >= 3:  return 80
    if x >= 1:  return 60
    if x >= 0:  return 40
    return 10


# ======================================================
# ⭐ 動態權重 A2 分數（缺資料自動調整權重）
# ======================================================

def calc_a2_dynamic(metrics):
    """
    metrics = {"pe":xx, "pb":xx, "ps":xx, "roe":xx, "roa":xx, "revenue":xx, "eps":xx}
    """

    scores = {
        "pe": score_pe(metrics.get("pe")),
        "pb": score_pb(metrics.get("pb")),
        "ps": score_ps(metrics.get("ps")),
        "roe": score_roe(metrics.get("roe")),
        "roa": score_roa(metrics.get("roa")),
        "revenue": score_revenue(metrics.get("revenue")),
        "eps": score_eps(metrics.get("eps")),
    }

    weights = {
        "pe": 20,
        "pb": 10,
        "ps": 10,
        "roe": 20,
        "roa": 20,
        "revenue": 10,
        "eps": 10,
    }

    valid_scores = {k: v for k, v in scores.items() if metrics.get(k) is not None}
    valid_weights = {k: weights[k] for k in valid_scores.keys()}

    if not valid_scores:
        return 0, scores, {}

    total_w = sum(valid_weights.values())
    norm_w = {k: valid_weights[k] / total_w for k in valid_weights}

    final = 0
    for k in valid_scores:
        final += valid_scores[k] * norm_w[k]

    final = round(final, 2)

    return final, scores, norm_w
