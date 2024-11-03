import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import pandas as pd
from loguru import logger
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




