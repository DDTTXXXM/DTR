import streamlit as st
import pandas as pd
import numpy as np

# 顯示標題與作者資訊
st.write("作者：QQQ9527")

# === 1. Wi‑Fi 7 頻段參數設定 ===
wifi7_freq_options = {
    "2.4GHz": {
        "freq_mhz": 2450,    # 中心頻率 (MHz)
        "rx_ant_gain": -4.3  # Rx 天線增益 (dBi)
    },
    "5GHz-6GHz": {
        "freq_mhz": 5500,
        "rx_ant_gain": -5.3
    },
    "6GHz-7.2GHz": {
        "freq_mhz": 6600,
        "rx_ant_gain": -6.3
    }
}

# === 2. 定義環境與對應路徑損耗指數 ===
# 參考文件：
# - In building (Soft Cubicle Partition): n = 3.5
# - Outdoor (Shadowed Urban Area): n = 5.0
environments = {
    "In building": 3.5,
    "Outdoor": 5.0
}

# === 3. 路徑損耗模型 (對數路徑損耗) ===
# PL(d) = 20*log10(freq_mhz) - 27.55 + 10*n*log10(d)
# Rx = Tx + G_tx + G_rx - PL(d)
# 解得： d = 10 ^ ((Tx + G_tx + G_rx - Rx - [20*log10(freq_mhz) - 27.55]) / (10*n))
def calculate_distance_pathloss(tx_power, tx_gain, rx_gain, rx_level, freq_mhz, n):
    """計算在給定參數下的可達距離"""
    constant = 20 * np.log10(freq_mhz) - 27.55  # 1 m 處的基本損耗
    total_loss = tx_power + tx_gain + rx_gain - rx_level
    exponent = (total_loss - constant) / (10 * n)
    d = 10 ** exponent
    return d

# === 4. Rx 閾值設定：從 -40 到 -120 (每 1 dB) ===
rx_thresholds = list(range(-40, -121, -1))

# === 5. 根據使用者選擇的 Tx Power 產生資料表 ===
def generate_dataframe(tx_power):
    results = []
    for rx in rx_thresholds:
        row = {"Rx (dBm)": rx}
        # 對每個頻段與環境計算距離
        for band, params in wifi7_freq_options.items():
            for env_name, path_loss_exponent in environments.items():
                distance = calculate_distance_pathloss(
                    tx_power=tx_power,      # 使用者選擇的 Tx Power
                    tx_gain=0,              # AP 天線增益假設為 0
                    rx_gain=params["rx_ant_gain"],
                    rx_level=rx,
                    freq_mhz=params["freq_mhz"],
                    n=path_loss_exponent
                )
                row[f"{band} {env_name} (m)"] = distance
        results.append(row)
    df = pd.DataFrame(results)
    return df

# === 6. Streamlit UI 設定 ===
st.title("Wi‑Fi 7 頻段 Rx ↔ 距離 對照表 UI")

# 6.1 Tx Power 下拉選單：0 ~ 30 dBm，每 0.5 dB 增減
tx_power_list = [i * 0.5 for i in range(0, 61)]
selected_tx_power = st.selectbox("選擇 Tx Power (dBm)", tx_power_list)

# 6.2 產生對照表 (根據選擇的 Tx Power)
df = generate_dataframe(selected_tx_power)

# 6.3 查詢模式下拉選單：依 Rx 門檻 或 依 距離
mode = st.selectbox("請選擇查詢模式：", ["依 Rx 門檻", "依 距離"])

if mode == "依 Rx 門檻":
    # 使用者選擇 Rx 門檻 (dBm)
    rx_input = st.selectbox("選擇 Rx 門檻 (dBm)", rx_thresholds)
    filtered_df = df[df["Rx (dBm)"] == rx_input]
    st.subheader(f"查詢結果：Rx = {rx_input} dBm, Tx Power = {selected_tx_power} dBm")
    st.dataframe(filtered_df)
    
elif mode == "依 距離":
    # 先選擇頻段與環境，再輸入目標距離
    band = st.selectbox("選擇頻段", list(wifi7_freq_options.keys()))
    env = st.selectbox("選擇環境", list(environments.keys()))
    column_name = f"{band} {env} (m)"
    
    distance_input = st.number_input("輸入距離 (m)", min_value=0.0, value=50.0)
    
    # 找出該頻段與環境下距離最接近輸入值的資料
    df["diff"] = abs(df[column_name] - distance_input)
    nearest_row = df.loc[df["diff"].idxmin()]
    
    st.subheader(f"在 {band} - {env} 模式下，最接近 {distance_input} m 的結果 (Tx Power = {selected_tx_power} dBm)")
    st.write(f"對應的 Rx 門檻：{nearest_row['Rx (dBm)']} dBm")
    st.write(f"實際距離：{nearest_row[column_name]:.2f} m")
    st.dataframe(nearest_row.drop("diff"))

