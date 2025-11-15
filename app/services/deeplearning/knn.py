# knn.py — 傳統機器學習骨架
def predict(symbol, horizon=5):
    return {
        "model": "knn",
        "symbol": symbol,
        "horizon": horizon,
        "prob_up": 0.51,
        "prob_down": 0.49,
    }
