import streamlit as st
import pandas as pd
import numpy as np
# pip install streamlit-folium
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium
from menu import menu
import geopandas as gpd
from shapely.geometry import Point

menu()

# Load county GeoJSON data (you'll need to provide the correct file path)
counties = gpd.read_file('data/Tainan_County.geojson')
df = pd.read_csv("data/map.csv")
df = df[df['交易年份']>=2022]

housetype = np.array(["住商大樓", "公寓", "透天厝", "其他"])
materialtype = np.array(["鋼骨", "鋼筋", "磚石", "竹木"])
YNtype = np.array(["有", "無"])

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半徑，單位：公里
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# Create a base map without any tiles
m = folium.Map(
    location=[23.13, 120.312480],
    zoom_start=10,
    # tiles=None
)

# 添加縣界GeoJSON圖層
folium.GeoJson(
    counties,
    style_function=lambda feature: {
        'fillColor': 'white',
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.4,
    }
).add_to(m)

# Use st_folium to display the map and get the click data
map_data = st_folium(m, width=1000, height=500, key="map")

# if map_data['last_clicked']:
#     clicked_lat = map_data['last_clicked']['lat']
#     clicked_lon = map_data['last_clicked']['lng']
    
#     # 添加新標記
#     folium.Marker(
#         [clicked_lat, clicked_lon],
#         popup='您選擇的位置',
#         tooltip='點擊查看詳情'
#     ).add_to(m)
    
#     # 重新顯示更新後的地圖
#     st_folium(m, width=1000, height=500, key="map")

with st.form("input_form"):
    col1, col2, col3, col4, col5 = st.columns(5)
    # 在每個列中放置一個選擇框
    with col1:
        house = st.selectbox("建築型態", housetype, key='select1')
    with col2:
        material = st.multiselect("主要建材", materialtype, key='select2', default=materialtype[1])
    with col3:
        parking = st.radio("有無車位", YNtype, key='select3')
    with col4:
        age = st.number_input("屋齡", min_value=0, max_value=100, value=5)
    with col5:
        area = st.number_input("房屋坪數", min_value=0.5, value=float(30), step=0.1)
    # 添加一個提交按鈕
    submit_button = st.form_submit_button("Submit")

if submit_button:
    clicked_lat = map_data['last_clicked']['lat']
    clicked_lon = map_data['last_clicked']['lng']
    st.write(f"點擊位置的經緯度: {clicked_lat}, {clicked_lon}")
    point = Point(clicked_lon, clicked_lat)

    town = ""

    # 判斷行政區
    for index, row in counties.iterrows():
        if row['geometry'].contains(point):
            # st.write(f"行政區: {row['TOWN']}")
            town = row['TOWN']
            # st.write(f"行政區: {town}")
            break
    # st.write(f"行政區: {town}")
    st.write("You selected:")
    st.write(f"建築型態: {house}")
    st.write(f"主要建材: {', '.join(material) if material else 'None'}")
    st.write(f"有無車位: {parking}")
    st.write(f"屋齡: {age}")
    st.write(f"房屋坪數: {area}")
    st.write(f"行政區: {town}")


    # 計算每一列與給定經緯度的距離並更新 DataFrame
    df['distance'] = df.apply(lambda row: haversine(clicked_lat, clicked_lon, row['緯度'], row['經度']), axis=1)

    # 找到距離最短的點
    closest_price = df.loc[df['distance'].idxmin(), '單價元每坪']
    closest_ID = df.loc[df['distance'].idxmin(), '編號']

    # 顯示結果
    st.write(f"單價元每坪: {round(closest_price, 2)}")
    # st.write(f"單價元每坪: {closest_ID}")
