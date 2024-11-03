import torch
import numpy as np
import pandas as pd
import json
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from matplotlib import rcParams


class LSTMModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim, dropout):
        super(LSTMModel, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # === 定義全連接層（前置 Dense 層）===
        # self.pre_dense1 = nn.Linear(input_dim, 128)  # 將輸入維度轉為 128
        # self.pre_dense2 = nn.Linear(128, 64)  # 將 128 維轉為 64 維
        # self.pre_dense_activation = nn.GELU()  # 激活函數
        # self.dropout = nn.Dropout(dropout)  # Dropout

        # === 定義 LSTM 層 ===
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # === 定義後續的全連接層 ===
        # self.fc1 = nn.Linear(hidden_dim*31, 8)
        self.fc1 = nn.Linear(hidden_dim, 8)
        # self.bn1 = nn.BatchNorm1d(32)
        self.fc2 = nn.Linear(8, 4)
        # self.bn2 = nn.BatchNorm1d(8)
        self.fc3 = nn.Linear(4, output_dim)

        # 激活函數
        self.gelu = nn.GELU()
        self.tahn = nn.Tanh()
        self.flatten = nn.Flatten()

    def forward(self, x):
        # === 通過 Dense 層處理輸入 ===
        # out = self.pre_dense1(x)
        # out = self.pre_dense_activation(out)
        # out = self.dropout(out)

        # out = self.pre_dense2(out)
        # out = self.pre_dense_activation(out)
        # out = self.dropout(out)

        # 初始化 LSTM 的隱藏狀態和細胞狀態
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)

        # === 前向傳播 LSTM ===
        out, _ = self.lstm(
            x, (h0, c0)
        )  # LSTM 層輸入形狀 (batch_size, time_steps, input_size)
        out = out[:, -1, :]  # 取最後一個時間步的輸出
        # out = self.flatten(out)
        # out = out.reshape(out.size(0), -1)

        # === 通過後續的全連接層 ===
        out = self.tahn(self.fc1(out))
        out = self.gelu(self.fc2(out))
        out = self.fc3(out)

        return out

# Load your CSV file (make sure it has the same features used in training)
df = pd.read_csv("房價_add南科and股價 (1).csv")

# Ensure the data is sorted and preprocessed similarly
df["交易年月日"] = pd.to_datetime(df["交易年月日"])
df = df.sort_values("交易年月日")

# Your numerical and one-hot feature columns
numerical_features =[
    "單價元每坪",
    "建物移轉總面積平方公尺",
    # "time_diff",
    # "cumulative_time",
    "建物現況格局-房",
    "建物現況格局-廳",
    "建物現況格局-衛",
    "建物現況格局-隔間",
    "屋齡",
    # "營業額總計",
    "stockTW",
    "KDE_0.5km",
    "KDE_1km",
    "KDE_1.5km",
    # "KDE_class",
    "good_count_0_500",
    "good_count_500_1000",
    "good_count_1000_1500",
    "bad_count_0_500",
    "bad_count_500_1000",
    "bad_count_1000_1500",
]
one_hot_features = [
    "建築型態_住商大樓",
    "建築型態_公寓",
    "建築型態_其他",
    "建築型態_透天厝",
    "是否包含車位",
    "建材_磚石",
    "建材_鋼筋",
    "建材_鋼骨",
    "建材_竹木",
    "住",
    "商",
    "工",
    "農",
    "移轉層次_騎樓",
    "移轉層次_屋頂",
    "移轉層次_一二樓",
    "鄉鎮_七股區",
    "鄉鎮_下營區",
    "鄉鎮_中西區",
    "鄉鎮_仁德區",
    "鄉鎮_佳里區",
    "鄉鎮_六甲區",
    "鄉鎮_北區",
    "鄉鎮_北門區",
    "鄉鎮_南化區",
    "鄉鎮_南區",
    "鄉鎮_善化區",
    "鄉鎮_大內區",
    "鄉鎮_學甲區",
    "鄉鎮_安南區",
    "鄉鎮_安定區",
    "鄉鎮_安平區",
    "鄉鎮_官田區",
    "鄉鎮_將軍區",
    "鄉鎮_山上區",
    "鄉鎮_左鎮區",
    "鄉鎮_後壁區",
    "鄉鎮_新化區",
    "鄉鎮_新市區",
    "鄉鎮_新營區",
    "鄉鎮_東區",
    "鄉鎮_東山區",
    "鄉鎮_柳營區",
    "鄉鎮_楠西區",
    "鄉鎮_歸仁區",
    "鄉鎮_永康區",
    "鄉鎮_玉井區",
    "鄉鎮_白河區",
    "鄉鎮_西港區",
    "鄉鎮_關廟區",
    "鄉鎮_鹽水區",
    "鄉鎮_麻豆區",
    "鄉鎮_龍崎區",
]

# 目標變數
target_feature = ["單價元每坪"]

# Extract features
numerical_data = df[numerical_features].values
one_hot_data = df[one_hot_features].values


# Convert to PyTorch tensors
numerical_tensor = torch.FloatTensor(numerical_data)
one_hot_tensor = torch.FloatTensor(one_hot_data)

# Combine numerical and one-hot features
X = np.hstack([numerical_data, one_hot_data])
X_tensor = torch.FloatTensor(X)
X_tensor = X_tensor.unsqueeze(1)  # Add an extra dimension if needed


model = torch.load("LSTM_model1101.pth")