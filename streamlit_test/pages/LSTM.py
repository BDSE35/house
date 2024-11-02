import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
# pip install streamlit-folium
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium
from menu import menu

menu()

m = folium.Map(location=[23.13, 120.312480], zoom_start=10)

# Use st_folium to display the map and get the click data
map_data = st_folium(m, width=700, height=500)

# Check if the map was clicked
if map_data['last_clicked']:
    clicked_lat = map_data['last_clicked']['lat']
    clicked_lon = map_data['last_clicked']['lng']
    st.write(f"點擊位置的經緯度: {clicked_lat}, {clicked_lon}")

with st.expander("南科聚落", expanded=True):
    st.page_link("pages/DBSCAN.py", label="聚落分布", icon="🔐")
    st.page_link("pages/KDE.py", label="交易密度", icon="👤")