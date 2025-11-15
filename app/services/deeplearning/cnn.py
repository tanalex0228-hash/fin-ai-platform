# app/services/deeplearning/cnn.py
import numpy as np
import pandas as pd

# 之後你可以用 tensorflow/keras 或 pytorch
# 目前先寫介面骨架，之後慢慢充實

def prepare_cnn_dataset(df: pd.DataFrame, window_size: int = 30):
    """
    把價格序列轉成 (samples, timesteps, features) 格式
    """
    # TODO: 實作
    pass

def train_cnn_model(X_train, y_train):
    """
    建立並訓練 CNN 模型
    """
    # TODO: keras.Sequential(...)...
    pass

def predict_cnn(model, X):
    """
    使用已訓練的 CNN 做預測
    """
    # TODO: return model.predict(X)
    pass
