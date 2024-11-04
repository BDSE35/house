from flask import Flask, render_template, request
import pandas as pd
import altair as alt
import numpy as np
import pydeck as pdk
import json


app = Flask(__name__)



# 繪畫圖表
def create_chart_altair(df, columns, title):
    chart_data = df[columns].reset_index()  # 重置索引以便 Altair 正確處理
    chart = alt.Chart(chart_data).transform_fold(
        columns,
        as_=['Category', 'Value']
    ).mark_line().encode(
        x='西元年月:T',
        y='Value:Q',
        color=alt.Color('Category:N', legend=alt.Legend(orient='right'))
    ).properties(
        width=800,
        height=400,
        title=title
    )
    return chart

def remove_unnecessary_keys(chart_json_str):
    # 解析 JSON 字符串為 Python 字典
    chart_json = json.loads(chart_json_str)
    
    # 移除不必要的屬性
    chart_json.pop('datasets', None)
    chart_json.pop('config', None)
    
    # 將字典重新轉換為 JSON 字符串
    return json.dumps(chart_json)


# 首頁
@app.route('/')
def index():
    return render_template('index.html')


# 載入台南地圖的 GeoJSON
def load_geojson_data():
    with open("data/Tainan_County.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    return geojson_data

# Load the mapdata once at startup
geojson_data = load_geojson_data()

@app.route("/map")
def map():
    # Create PyDeck layer with the GeoJSON data
    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson_data,
        opacity=1.0,
        stroked=True,
        filled=False,
        wireframe=True,
        get_line_color=[255, 0, 0],
        get_line_width=80,
    )

    # Define the PyDeck map
    deck = pdk.Deck(
        map_style=None,
        initial_view_state={
            "latitude": 23.13,
            "longitude": 120.312480,
            "zoom": 9,
            "pitch": 10,
        },
        layers=[layer],
    )

    # Convert the PyDeck object to JSON
    deck_json = deck.to_json()

    return render_template("map.html", deck_json=deck_json)


# 科學園區part
def load_science_data():
    df = pd.read_csv("data/park1015.csv", encoding='utf-8-sig')
    df = df.drop(columns='平均單價元平方公尺', errors='ignore')  # Drop specified column
    if '西元年月' in df.columns:
        df.sort_values('西元年月', inplace=True)
        df.set_index('西元年月', inplace=True)
    else:
        raise ValueError("欄位 '西元年月' 不存在於資料中，請檢查資料檔案。")
    return df

# Load park1015.csv once at startup
df_science = load_science_data()

@app.route('/southern_taiwan_science_park', methods=['GET', 'POST'])
def southern_taiwan_science_park():
    default_columns1 = ['博士', '碩士', '大學', '專科', '高中', '其他學歷']
    default_columns2 = ['積體電路營業額(億元)', '光電營業額(億元)', '電腦及周邊營業額(億元)', '通訊營業額(億元)', '精密機械營業額(億元)', '生物技術營業額(億元)', '其他營業額']
    default_columns3 = ['用水量(CMD)', '污水處理量(CMD)']

    chart1 = create_chart_altair(df_science, default_columns1, "南科各項指標 - 學歷")
    chart2 = create_chart_altair(df_science, default_columns2, "南科各項指標 - 營業額")
    chart3 = create_chart_altair(df_science, default_columns3, "南科各項指標 - 用水量和污水處理量")

    # Convert charts to JSON strings
    chart1_json = remove_unnecessary_keys(chart1.to_json())
    chart2_json = remove_unnecessary_keys(chart2.to_json())
    chart3_json = remove_unnecessary_keys(chart3.to_json())

    # print("Chart 1 JSON:", chart1_json)
    # print("Chart 2 JSON:", chart2_json)
    # print("Chart 3 JSON:", chart3_json)

    # Retrieve selected columns from the form submission
    selected_columns = request.form.getlist("columns")
    # print("Selected columns:", selected_columns)  # Debug: check selected columns
    selected_chart_json = None
    if selected_columns:
        selected_chart = create_chart_altair(df_science, selected_columns, "選擇的指標")
        selected_chart_json = json.dumps(json.loads(selected_chart.to_json()))
        # print(selected_chart_json)  # Debug: check if JSON was created

    return render_template("southern_taiwan_science_park.html", 
                           chart1_json=chart1_json, 
                           chart2_json=chart2_json, 
                           chart3_json=chart3_json,
                           selected_chart_json=selected_chart_json,
                           columns=df_science.columns)


# DBscan & KDE
def load_map_data():
    df = pd.read_csv("data/map.csv")
    return df

# Load the map.scv once at startup
df_map = load_map_data()


@app.route('/dbscan', methods=['GET', 'POST'])
def dbscan():
    year_min = int(df_map['交易年份'].min()) + 1
    year_max = int(df_map['交易年份'].max()) - 1
    
    # Default to the minimum year, or use selected year from form submission
    selected_year = request.form.get("year", year_min)
    selected_year = int(selected_year)
    
    # Filter the data based on the selected year
    map_data = df_map[df_map['交易年份'] == selected_year][['經度', '緯度', 'Region']]
    map_data = map_data.rename(columns={'經度': 'longitude', '緯度': 'latitude'})
    
    # 移除含有 NaN 值的行
    map_data = map_data.dropna()

    # Map 'Region' to colors
    def get_color(region):
        color_map = {
            "A": [255, 0, 0],    # Red
            "B": [0, 255, 0],    # Green
            "C": [0, 0, 255],    # Blue
            "D": [255, 255, 0],  # Yellow
            "E": [255, 165, 0],  # Orange
            "F": [128, 0, 128]   # Purple
        }
        return color_map.get(region, [0, 0, 0])  # Default to black if region is not in A-F

    # Apply the color function to the data
    map_data['color'] = map_data['Region'].apply(get_color)

    # Create PyDeck layer using the map data with colors based on 'Region'
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_data,
        get_position='[longitude, latitude]',
        get_radius=100,
        get_fill_color='color',
        opacity=1.0,
    )

    # Define the PyDeck map
    deck = pdk.Deck(
        map_style=None,
        initial_view_state={
            "latitude": 23.13,
            "longitude": 120.312480,
            "zoom": 9,
            "pitch": 10,
        },
        layers=[layer],
    )

    # Render the map to JSON
    deck_json = deck.to_json()

    return render_template("dbscan.html", deck_json=deck_json, year_min=year_min, year_max=year_max, selected_year=selected_year)



@app.route('/kde', methods=['GET', 'POST'])
def kde():
    year_min = int(df_map['交易年份'].min()) + 1
    year_max = int(df_map['交易年份'].max()) - 1
    
    # Default to the minimum year, or use selected year from form submission
    selected_year = request.form.get("year", year_min)
    selected_year = int(selected_year)
    
    # Filter the data based on the selected year
    map_data = df_map[df_map['交易年份'] == selected_year][['經度', '緯度', 'KDE_class']]
    map_data = map_data.rename(columns={'經度': 'longitude', '緯度': 'latitude'})

    # Map 'KDE_class' to colors
    def get_color(region):
        color_map = {
            1: [255, 0, 0],    # Red
            2: [0, 255, 0],    # Green
            3: [0, 0, 255],    # Blue
        }
        return color_map.get(region, [0, 0, 0])  # Default to black if not in 1-3

    # Apply the color function to the data
    map_data['color'] = map_data['KDE_class'].apply(get_color)

    # Create PyDeck layer using the map data with colors based on 'KDE_class'
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_data,
        get_position='[longitude, latitude]',
        get_radius=100,
        get_fill_color='color',
        opacity=1.0,
    )

    # Define the PyDeck map
    deck = pdk.Deck(
        map_style=None,
        initial_view_state={
            "latitude": 23.13,
            "longitude": 120.312480,
            "zoom": 9,
            "pitch": 10,
        },
        layers=[layer],
    )

    # Render the map to JSON
    deck_json = deck.to_json()

    return render_template("kde.html", deck_json=deck_json, year_min=year_min, year_max=year_max, selected_year=selected_year)




'''
for RF_all
'''
# Load data for feature importance (2012-2017 and 2018-2023)
rf_data_2012_2017 = {
    'Feature': ['南科房屋交易密度1km', '建物移轉總面積坪', '屋齡區間_未滿3年', '嫌惡設施_1000m_1500m',
                '嫌惡設施_500m_1000m', '迎毗設施_1000m_1500m', '嫌惡設施_0m_500m', '建材種類_鋼筋',
                '交易日', '迎毗設施_500m_1000m'],
    'Importance': [0.161147, 0.144616, 0.123807, 0.086624, 0.046105, 0.042527, 
                   0.035032, 0.029498, 0.028447, 0.027357]
}

rf_data_2018_2023 = {
    'Feature': ['南科房屋交易密度1km', '屋齡區間_21年以上－未滿30年', '陽台有無', '嫌惡設施_1000m_1500m',
                '建物移轉總面積坪', '是否包含車位', '嫌惡設施_500m_1000m', '嫌惡設施_0m_500m',
                '迎毗設施_1000m_1500m', '迎毗設施_500m_1000m'],
    'Importance': [0.203884, 0.105928, 0.092646, 0.080877, 0.070971, 0.053769, 
                   0.042363, 0.038192, 0.032098, 0.031010]
}

# Create DataFrames
rf_df_2012_2017 = pd.DataFrame(rf_data_2012_2017)
rf_df_2018_2023 = pd.DataFrame(rf_data_2018_2023)

# Combined feature importance data
rf_data = {
    "year": [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "屋齡等級": [0.212276, 0.161982, 0.180656, 0.197343, 0.193817, 0.154248, 0.151360, 0.145616, 0.174389, 0.165569, 0.138923, 0.137386],
    "建物移轉總面積坪": [0.204430, 0.198052, 0.179977, 0.163105, 0.173457, 0.181475, 0.168218, 0.122992, 0.123445, 0.106105, 0.091251, 0.101763],
    "KDE_1km": [0.172320, 0.215064, 0.264660, 0.221705, 0.261713, 0.227436, 0.228081, 0.294876, 0.264986, 0.277946, 0.238179, 0.187211],
    "外圍嫌惡設施": [0.098329, 0.094806, 0.077010, 0.096296, 0.073067, 0.098365, 0.117224, 0.077063, 0.097850, 0.081301, 0.063514, 0.064936],
    "外圍迎毗設施": [0.077337, 0.065225, 0.047151, 0.056002, 0.052789, 0.053996, 0.046686, 0.047813, 0.054786, 0.033012, 0.030797, 0.033254],
}

df_rf_combined = pd.DataFrame(rf_data)
rf_df_melted = df_rf_combined.melt(id_vars=["year"], var_name="Feature", value_name="Importance")

# Create Altair charts
def create_chart(df, title):
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Importance', title="特徵重要性"),
        y=alt.Y('Feature', sort='-x', title=title),
        color='Feature:N',
        tooltip=['Feature', 'Importance']
    ).properties(
        width=800,
        height=400
    )
    return chart

rf_chart_2012_2017 = create_chart(rf_df_2012_2017, "2012-2017 特徵")
rf_chart_2018_2023 = create_chart(rf_df_2018_2023, "2018-2023 特徵")

# Stacked bar chart for yearly importance
rf_stacked_chart = alt.Chart(rf_df_melted).mark_bar().encode(
    x=alt.X("year:N", title="Year"),
    y=alt.Y("Importance:Q", stack="zero", title="Cumulative Importance"),
    color="Feature:N",
    tooltip=["Feature", "Importance"]
).properties(
    width=800,
    height=400
)

# Convert charts to JSON for embedding in HTML
rf_chart_2012_2017_json = rf_chart_2012_2017.to_json()
rf_chart_2018_2023_json = rf_chart_2018_2023.to_json()
rf_stacked_chart_json = rf_stacked_chart.to_json()

@app.route('/rf_all')
def rf_all():
    return render_template(
        "rf_all.html",
        rf_chart_2012_2017_json=rf_chart_2012_2017_json,
        rf_chart_2018_2023_json=rf_chart_2018_2023_json,
        rf_stacked_chart_json=rf_stacked_chart_json
    )


'''
for xg_all
'''
# Data for feature importance
xg_data_2012_2017 = {
    'Feature': ['屋齡區間_未滿3年', '建材種類_鋼筋', '屋齡區間_12年以上－未滿21年', '建築型態_公寓', 
                '建材種類_未知', '屋齡區間_21年以上－未滿30年', '屋齡區間_3年以上－未滿12年', 
                '屋齡區間_30年以上', '南科房屋交易密度1km', '建築型態_其他'],
    'Importance': [0.202681, 0.099877, 0.097316, 0.080442, 0.072742, 0.052455, 
                   0.034760, 0.025517, 0.025161, 0.025105]
}

xg_data_2018_2023 = {
    'Feature': ['屋齡區間_21年以上－未滿30年', '陽台有無', '建築型態_公寓', '是否包含車位', 
                '土地用途_未知', '南科房屋交易密度1km', '屋齡區間_12年以上－未滿21年', 
                '屋齡區間_3年以上－未滿12年', '屋齡區間_未滿3年', '建材種類_磚石'],
    'Importance': [0.310060, 0.113863, 0.108146, 0.095158, 0.042647, 0.022632, 
                   0.022046, 0.020895, 0.018399, 0.017951]
}

# Create DataFrames
xg_df_2012_2017 = pd.DataFrame(xg_data_2012_2017)
xg_df_2018_2023 = pd.DataFrame(xg_data_2018_2023)

# Combined feature importance data
xg_data = {
    "year": [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "屋齡等級": [0.329273, 0.210073, 0.289471, 0.324261, 0.278667, 0.273782, 0.261632, 0.241245, 0.242537, 0.249110, 0.135712, 0.159118],
    "有無電梯": [0.132175, 0.074796, 0.073288, 0.101453, 0.108569, 0.115470, 0.158196, 0.086267, 0.055491, 0.035112, 0.021067, 0.015827],
    "新型建材": [0.089081, 0.086640, 0.116456, 0.122060, 0.181700, 0.074802, 0.046172, 0.048967, 0.019804, 0.021122, 0.011137, 0.017675],
    "外圍迎毗設施": [0.072234, 0.056972, 0.041239, 0.041141, 0.040006, 0.044667, 0.040219, 0.038469, 0.044641, 0.019576, 0.015764, 0.018332],
}

xg_df_combined = pd.DataFrame(xg_data)
xg_df_melted = xg_df_combined.melt(id_vars=["year"], var_name="Feature", value_name="Importance")

# Create Altair charts
def create_chart(df, title):
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Importance', title="特徵重要性"),
        y=alt.Y('Feature', sort='-x', title=title),
        color='Feature:N',
        tooltip=['Feature', 'Importance']
    ).properties(
        width=800,
        height=400
    )
    return chart

xg_chart_2012_2017 = create_chart(xg_df_2012_2017, "2012-2017 特徵")
xg_chart_2018_2023 = create_chart(xg_df_2018_2023, "2018-2023 特徵")

# Stacked bar chart for yearly importance
xg_stacked_chart = alt.Chart(xg_df_melted).mark_bar().encode(
    x=alt.X("year:N", title="Year"),
    y=alt.Y("Importance:Q", stack="zero", title="Cumulative Importance"),
    color="Feature:N",
    tooltip=["Feature", "Importance"]
).properties(
    width=800,
    height=400
)

# Convert charts to JSON for embedding in HTML
xg_chart_2012_2017_json = xg_chart_2012_2017.to_json()
xg_chart_2018_2023_json = xg_chart_2018_2023.to_json()
xg_stacked_chart_json = xg_stacked_chart.to_json()


@app.route('/xg_all')
def xg_all():
    return render_template(
        'xg_all.html',
        xg_chart_2012_2017_json=xg_chart_2012_2017_json,
        xg_chart_2018_2023_json=xg_chart_2018_2023_json,
        xg_stacked_chart_json=xg_stacked_chart_json
        )


@app.route('/lstm')
def lstm():
    return render_template('lstm.html')




if __name__ == '__main__':
    app.run(debug=True)