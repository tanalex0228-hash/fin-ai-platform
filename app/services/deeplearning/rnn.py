# rnn.py — 深度學習骨架（之後會換成 LSTM）
def predict(symbol, horizon=5):
    return {
        "model": "rnn",
        "symbol": symbol,
        "horizon": horizon,
        "prob_up": 0.52,
        "prob_down": 0.48,
    }
