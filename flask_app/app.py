from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import numpy as np
import folium
import geopandas as gpd
from shapely.geometry import Point
from folium import Popup, Icon
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
import json
from haversine import haversine
import altair as alt
import pydeck as pdk
import os
import configparser
from matplotlib import rcParams

# 设置字体为 Microsoft YaHei（微軟正黑體）

rcParams["font.sans-serif"] = ["Microsoft YaHei"]
rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


app = Flask(__name__)

# 获取 .flask/config.ini 文件的路径
config_path = os.path.join(os.path.dirname(__file__), ".flask", "config.ini")

# 初始化配置解析器
config = configparser.ConfigParser()
config.read(config_path)

# 将 secret_key 设置到 Flask 应用
app.secret_key = config["flask"]["secret_key"]


# 繪畫圖表
def create_chart_altair(data, columns, title):
    melted_df = data.reset_index().melt(
        id_vars="西元年月", value_vars=columns, var_name="Category", value_name="Value"
    )

    # 過濾掉 Value 欄位中的 NaN 或無限值
    melted_df = melted_df[
        (~melted_df["Value"].isnull())
        & (melted_df["Value"] != np.inf)
        & (melted_df["Value"] != -np.inf)
    ]

    chart = (
        alt.Chart(melted_df)
        .mark_line()
        .encode(
            x=alt.X("西元年月:T", title="日期", axis=alt.Axis(labelAngle=45)),
            y=alt.Y("Value:Q", title="數值"),
            color=alt.Color("Category:N", title="類別"),
        )
        .properties(title=title, width=800, height=400)
    )
    return chart


# 首頁
@app.route("/")
def index():
    return render_template("index.html")


# 科學園區part
def load_science_data():
    # 載入數據，並解析日期欄位 "西元年月" 為日期格式
    df = pd.read_csv("data/park1015.csv", encoding="utf-8-sig")

    # 確保 "西元年月" 為索引
    if "西元年月" in df.columns:
        df.set_index("西元年月", inplace=True)
    else:
        raise ValueError("欄位 '西元年月' 不存在於資料中，請檢查資料檔案。")

    # 刪除無效日期的行
    df = df[df.index.notna()]

    # 將其他非數值欄位轉換為數值，無法轉換的設為 NaN
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 刪除包含無效數值的行
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    return df


# 測試加載數據
df_science = load_science_data()


@app.route("/southern_taiwan_science_park", methods=["GET", "POST"])
def southern_taiwan_science_park():
    default_columns1 = ["博士", "碩士", "大學", "專科", "高中", "其他學歷"]
    default_columns2 = [
        "積體電路營業額(億元)",
        "光電營業額(億元)",
        "電腦及周邊營業額(億元)",
        "通訊營業額(億元)",
        "精密機械營業額(億元)",
        "生物技術營業額(億元)",
        "其他營業額",
    ]
    default_columns3 = ["用水量(CMD)", "污水處理量(CMD)"]

    chart1 = create_chart_altair(df_science, default_columns1, "南科各項指標 - 學歷")
    chart2 = create_chart_altair(df_science, default_columns2, "南科各項指標 - 營業額")
    chart3 = create_chart_altair(
        df_science, default_columns3, "南科各項指標 - 用水量和污水處理量"
    )

    chart1_json = chart1.to_json()
    chart2_json = chart2.to_json()
    chart3_json = chart3.to_json()
    # 獲取被選中的欄位
    selected_columns = request.form.getlist("columns")
    selected_chart_json = None
    if selected_columns:
        selected_chart = create_chart_altair(df_science, selected_columns, "選擇的指標")
        selected_chart_json = selected_chart.to_json()
        print("Selected columns:", selected_columns)
        print("Selected chart JSON:", selected_chart_json)

    return render_template(
        "southern_taiwan_science_park.html",
        chart1_json=chart1_json,
        chart2_json=chart2_json,
        chart3_json=chart3_json,
        selected_chart_json=selected_chart_json,
        columns=df_science.columns,
    )


# Load GeoJSON and CSV data
def load_geojson_data():
    with open("data/Tainan_County.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    return geojson_data


geojson_data = load_geojson_data()


def load_map_data():
    df = pd.read_csv("data/map.csv")
    return df


df_map = load_map_data()


# Create map with points
def create_map_with_points(selected_year=None):
    geo_layer = pdk.Layer(
        "GeoJsonLayer",
        geojson_data,
        opacity=1.0,
        stroked=True,
        filled=False,
        wireframe=True,
        get_line_color=[255, 0, 0],
        get_line_width=80,
    )

    # Filter map data based on year
    if selected_year:
        map_data = df_map[df_map["交易年份"] == selected_year]
        map_data = map_data.head(10)
        map_data = map_data.rename(columns={"經度": "longitude", "緯度": "latitude"})
    else:
        map_data = df_map.rename(columns={"經度": "longitude", "緯度": "latitude"})

    # Scatterplot layer for points
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        map_data,
        get_position="[longitude, latitude]",
        get_radius=100,
        get_fill_color="[255, 140, 0]",
        opacity=0.6,
    )

    # Initialize deck with OpenStreetMap tile style and MapView
    deck = pdk.Deck(
        map_style="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        initial_view_state=pdk.ViewState(
            latitude=23.13, longitude=120.31248, zoom=9, pitch=10
        ),
        layers=[geo_layer, scatter_layer],
    )

    return deck.to_json()


@app.route("/dbscan")
def dbscan():
    # year_min = int(df_map["交易年份"].min())
    # year_max = int(df_map["交易年份"].max())
    # selected_year = request.args.get("year", year_min)
    # selected_year = int(selected_year)

    # # 創建地圖的 JSON
    # deck_json = create_map_with_points(selected_year=selected_year)

    return render_template(
        "dbscan.html",
        # deck_json=deck_json,
        # year_min=year_min,
        # year_max=year_max,
        # selected_year=selected_year,
    )


@app.route("/kde")
def kde():
    # year_min = int(df_map["交易年份"].min())
    # year_max = int(df_map["交易年份"].max())
    # selected_year = request.args.get("year", year_min)
    # selected_year = int(selected_year)

    # 創建地圖的 JSON，僅顯示 KDE_class 的資料點
    # deck_json = create_map_with_points(selected_year=selected_year, kde_class=None)

    return render_template(
        "kde.html",
        # deck_json=deck_json,
        # year_min=year_min,
        # year_max=year_max,
        # selected_year=selected_year,
    )


"""
for RF_all
"""
# Load data for feature importance (2012-2017 and 2018-2023)
rf_data_2012_2017 = {
    "Feature": [
        "南科房屋交易密度1km",
        "建物移轉總面積坪",
        "屋齡區間_未滿3年",
        "嫌惡設施_1000m_1500m",
        "嫌惡設施_500m_1000m",
        "迎毗設施_1000m_1500m",
        "嫌惡設施_0m_500m",
        "建材種類_鋼筋",
        "交易日",
        "迎毗設施_500m_1000m",
    ],
    "Importance": [
        0.161147,
        0.144616,
        0.123807,
        0.086624,
        0.046105,
        0.042527,
        0.035032,
        0.029498,
        0.028447,
        0.027357,
    ],
}

rf_data_2018_2023 = {
    "Feature": [
        "南科房屋交易密度1km",
        "屋齡區間_21年以上－未滿30年",
        "陽台有無",
        "嫌惡設施_1000m_1500m",
        "建物移轉總面積坪",
        "是否包含車位",
        "嫌惡設施_500m_1000m",
        "嫌惡設施_0m_500m",
        "迎毗設施_1000m_1500m",
        "迎毗設施_500m_1000m",
    ],
    "Importance": [
        0.203884,
        0.105928,
        0.092646,
        0.080877,
        0.070971,
        0.053769,
        0.042363,
        0.038192,
        0.032098,
        0.031010,
    ],
}

# Create DataFrames
rf_df_2012_2017 = pd.DataFrame(rf_data_2012_2017)
rf_df_2018_2023 = pd.DataFrame(rf_data_2018_2023)

# Combined feature importance data
rf_data = {
    "year": [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "屋齡等級": [
        0.212276,
        0.161982,
        0.180656,
        0.197343,
        0.193817,
        0.154248,
        0.151360,
        0.145616,
        0.174389,
        0.165569,
        0.138923,
        0.137386,
    ],
    "建物移轉總面積坪": [
        0.204430,
        0.198052,
        0.179977,
        0.163105,
        0.173457,
        0.181475,
        0.168218,
        0.122992,
        0.123445,
        0.106105,
        0.091251,
        0.101763,
    ],
    "KDE_1km": [
        0.172320,
        0.215064,
        0.264660,
        0.221705,
        0.261713,
        0.227436,
        0.228081,
        0.294876,
        0.264986,
        0.277946,
        0.238179,
        0.187211,
    ],
    "外圍嫌惡設施": [
        0.098329,
        0.094806,
        0.077010,
        0.096296,
        0.073067,
        0.098365,
        0.117224,
        0.077063,
        0.097850,
        0.081301,
        0.063514,
        0.064936,
    ],
    "外圍迎毗設施": [
        0.077337,
        0.065225,
        0.047151,
        0.056002,
        0.052789,
        0.053996,
        0.046686,
        0.047813,
        0.054786,
        0.033012,
        0.030797,
        0.033254,
    ],
}

df_rf_combined = pd.DataFrame(rf_data)
rf_df_melted = df_rf_combined.melt(
    id_vars=["year"], var_name="Feature", value_name="Importance"
)


# Create Altair charts
def create_chart(df, title):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Importance", title="特徵重要性"),
            y=alt.Y("Feature", sort="-x", title=title),
            color="Feature:N",
            tooltip=["Feature", "Importance"],
        )
        .properties(width=800, height=400)
    )
    return chart


rf_chart_2012_2017 = create_chart(rf_df_2012_2017, "2012-2017 特徵")
rf_chart_2018_2023 = create_chart(rf_df_2018_2023, "2018-2023 特徵")

# Stacked bar chart for yearly importance
rf_stacked_chart = (
    alt.Chart(rf_df_melted)
    .mark_bar()
    .encode(
        x=alt.X("year:N", title="Year"),
        y=alt.Y("Importance:Q", stack="zero", title="Cumulative Importance"),
        color="Feature:N",
        tooltip=["Feature", "Importance"],
    )
    .properties(width=800, height=400)
)

# Convert charts to JSON for embedding in HTML
rf_chart_2012_2017_json = rf_chart_2012_2017.to_json()
rf_chart_2018_2023_json = rf_chart_2018_2023.to_json()
rf_stacked_chart_json = rf_stacked_chart.to_json()


@app.route("/rf_all", methods=["GET", "POST"])
def rf_all():
    return render_template(
        "rf_all.html",
        rf_chart_2012_2017_json=rf_chart_2012_2017_json,
        rf_chart_2018_2023_json=rf_chart_2018_2023_json,
        rf_stacked_chart_json=rf_stacked_chart_json,
    )


"""
for xg_all
"""
# Data for feature importance
xg_data_2012_2017 = {
    "Feature": [
        "屋齡區間_未滿3年",
        "建材種類_鋼筋",
        "屋齡區間_12年以上－未滿21年",
        "建築型態_公寓",
        "建材種類_未知",
        "屋齡區間_21年以上－未滿30年",
        "屋齡區間_3年以上－未滿12年",
        "屋齡區間_30年以上",
        "南科房屋交易密度1km",
        "建築型態_其他",
    ],
    "Importance": [
        0.202681,
        0.099877,
        0.097316,
        0.080442,
        0.072742,
        0.052455,
        0.034760,
        0.025517,
        0.025161,
        0.025105,
    ],
}

xg_data_2018_2023 = {
    "Feature": [
        "屋齡區間_21年以上－未滿30年",
        "陽台有無",
        "建築型態_公寓",
        "是否包含車位",
        "土地用途_未知",
        "南科房屋交易密度1km",
        "屋齡區間_12年以上－未滿21年",
        "屋齡區間_3年以上－未滿12年",
        "屋齡區間_未滿3年",
        "建材種類_磚石",
    ],
    "Importance": [
        0.310060,
        0.113863,
        0.108146,
        0.095158,
        0.042647,
        0.022632,
        0.022046,
        0.020895,
        0.018399,
        0.017951,
    ],
}

# Create DataFrames
xg_df_2012_2017 = pd.DataFrame(xg_data_2012_2017)
xg_df_2018_2023 = pd.DataFrame(xg_data_2018_2023)

# Combined feature importance data
xg_data = {
    "year": [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "屋齡等級": [
        0.329273,
        0.210073,
        0.289471,
        0.324261,
        0.278667,
        0.273782,
        0.261632,
        0.241245,
        0.242537,
        0.249110,
        0.135712,
        0.159118,
    ],
    "有無電梯": [
        0.132175,
        0.074796,
        0.073288,
        0.101453,
        0.108569,
        0.115470,
        0.158196,
        0.086267,
        0.055491,
        0.035112,
        0.021067,
        0.015827,
    ],
    "新型建材": [
        0.089081,
        0.086640,
        0.116456,
        0.122060,
        0.181700,
        0.074802,
        0.046172,
        0.048967,
        0.019804,
        0.021122,
        0.011137,
        0.017675,
    ],
    "外圍迎毗設施": [
        0.072234,
        0.056972,
        0.041239,
        0.041141,
        0.040006,
        0.044667,
        0.040219,
        0.038469,
        0.044641,
        0.019576,
        0.015764,
        0.018332,
    ],
}

xg_df_combined = pd.DataFrame(xg_data)
xg_df_melted = xg_df_combined.melt(
    id_vars=["year"], var_name="Feature", value_name="Importance"
)

xg_chart_2012_2017 = create_chart(xg_df_2012_2017, "2012-2017 特徵")
xg_chart_2018_2023 = create_chart(xg_df_2018_2023, "2018-2023 特徵")

# Stacked bar chart for yearly importance
xg_stacked_chart = (
    alt.Chart(xg_df_melted)
    .mark_bar()
    .encode(
        x=alt.X("year:N", title="Year"),
        y=alt.Y("Importance:Q", stack="zero", title="Cumulative Importance"),
        color="Feature:N",
        tooltip=["Feature", "Importance"],
    )
    .properties(width=800, height=400)
)

# Convert charts to JSON for embedding in HTML
# 檢查並轉換為 JSON 格式
xg_chart_2012_2017_json = (
    xg_chart_2012_2017.to_json() if xg_chart_2012_2017 is not None else "{}"
)
xg_chart_2018_2023_json = (
    xg_chart_2018_2023.to_json() if xg_chart_2018_2023 is not None else "{}"
)
xg_stacked_chart_json = (
    xg_stacked_chart.to_json() if xg_stacked_chart is not None else "{}"
)


@app.route("/xg_all")
def xg_all():

    # 渲染模板
    return render_template(
        "xg_all.html",
        xg_chart_2012_2017_json=xg_chart_2012_2017_json,
        xg_chart_2018_2023_json=xg_chart_2018_2023_json,
        xg_stacked_chart_json=xg_stacked_chart_json,
    )


# 加载数据
def load_geojson(filepath):
    try:
        return gpd.read_file(filepath)
    except Exception as e:
        print(f"无法加载 GeoJSON 文件: {e}")
        return None


def load_csv(filepath):
    try:
        df = pd.read_csv(filepath)
        return df[df["交易年份"] >= 2022]
    except Exception as e:
        print(f"无法加载地图数据: {e}")
        return None


# 加载地理数据
counties = gpd.read_file("data/Tainan_County.geojson")
df = pd.read_csv("data/newmap.csv")


# 計算哈弗辛距離
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半徑，單位：公里
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


@app.route("/lstm/map", methods=["GET"])
def render_lstm_map():
    m = folium.Map(location=[23.13, 120.312480], zoom_start=10)

    # 添加行政區界線 GeoJSON 層
    folium.GeoJson(
        counties,
        style_function=lambda feature: {
            "fillColor": "white",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.4,
        },
    ).add_to(m)

    # 添加代表南科的灰色標記
    folium.Marker(
        location=(23.11210179661455, 120.27042389614857),
        popup="南科",
        tooltip="南科",
        icon=Icon(color="gray"),
    ).add_to(m)

    # 如果 session 中有提交的資料，將動態標記添加到地圖
    if "submitted_data" in session:
        submitted_data = session["submitted_data"]
        popup_content = f"""
        <b>1.5KM內嫌惡設施:</b> {submitted_data['bad_count']}<br>
        <b>1.5KM內好設施:</b> {submitted_data['good_count']}<br>
        <b>{submitted_data['kde_class_display']}</b><br>
        <b>市場狀態:</b> {submitted_data['market_status']}<br>
        <b>預測價格:</b><br>
        {"".join([f"{date}: {price} 元<br>" for date, price in submitted_data['forecast_prices'].items()])}
        """
        folium.Marker(
            location=(submitted_data["lat"], submitted_data["lon"]),
            popup=folium.Popup(popup_content, max_width=300),
            icon=Icon(color="green"),
        ).add_to(m)

    # 將地圖轉為 HTML 格式並嵌入
    return m._repr_html_()


@app.route("/lstm", methods=["GET", "POST"])
def lstm():
    if request.method == "POST":
        lat = float(request.form.get("latitude"))
        lon = float(request.form.get("longitude"))
        area = float(request.form.get("area"))

        point = Point(lon, lat)
        town = ""

        # 判斷所點選的行政區
        for _, row in counties.iterrows():
            if row["geometry"].contains(point):
                town = row["TOWN"]
                break

        # 計算與其他位置的距離，並找到最近的點
        df["distance"] = df.apply(
            lambda row: haversine(lat, lon, row["緯度"], row["經度"]), axis=1
        )
        closest_row = df.loc[df["distance"].idxmin()]

        closest_price_per_ping = int(closest_row.get("單價元每坪", 0))
        bad_count_0_1500 = int(closest_row.get("bad_count_0_1500", 0))
        good_count_0_1500 = int(closest_row.get("good_count_0_1500", 0))
        KDE_class = str(closest_row.get("KDE_class", "無資料"))

        # 根據最近的編號取得預測價格
        forecast_dates = ["2024-12-01", "2025-01-01", "2025-02-01"]
        forecast_prices = {}
        for date in forecast_dates:
            matched_rows = df[
                (df["編號"] == closest_row["編號"]) & (df["Date"] == date)
            ]
            if not matched_rows.empty:
                forecast_prices[date] = int(matched_rows.iloc[0]["Predicted"])
            else:
                forecast_prices[date] = "無資料"

        actual_price = closest_price_per_ping * area
        market_status = "行情持平"
        predicted_price = forecast_prices.get("2025-02-01", "無資料")
        if isinstance(predicted_price, (int, float)):
            if predicted_price > actual_price:
                market_status = "行情看漲"
            elif predicted_price < actual_price:
                market_status = "行情看跌"

        # 生成並保存預測房價圖表
        dates = list(forecast_prices.keys())
        prices = [forecast_prices[date] for date in dates]
        fig, ax = plt.subplots()
        ax.plot(dates, prices, marker="o", linestyle="-")
        # ax.axhline(y=actual_price, color="red", linestyle="--", label="行情價")
        ax.set_xlabel("日期")
        ax.set_ylabel("預測價格 (元)")
        ax.set_title("未來房價預測")
        ax.legend()

        # 確保保存目錄存在
        if not os.path.exists("static/charts"):
            os.makedirs("static/charts")
        chart_path = f"static/charts/price_prediction_chart.png"
        fig.savefig(chart_path)
        plt.close(fig)

        # 保存提交的數據到 session 中
        session["submitted_data"] = {
            "lat": lat,
            "lon": lon,
            "bad_count": bad_count_0_1500,
            "good_count": good_count_0_1500,
            "kde_class_display": KDE_class,
            "forecast_prices": forecast_prices,
            "market_status": market_status,
            "chart_path": "/" + chart_path,
        }
        return jsonify(session["submitted_data"])

    return render_template("lstm.html")


if __name__ == "__main__":
    app.run(debug=True)
