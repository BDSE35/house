import json
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

from menu import menu

menu()

# Read the current page from the URL
# Sidebar navigation using expanders
# st.sidebar.title("Navigation")

# # Home Page Section
# with st.sidebar.expander("Home", expanded=True):
#     if st.button("Go to Home"):
#         page_name = "Home"
#     else:
#         page_name = "Home"

# # Data Page Section
# with st.sidebar.expander("Data", expanded=True):
#     if st.button("Go to Data"):
#         page_name = "Data"

# # About Page Section
# with st.sidebar.expander("About", expanded=True):
#     if st.button("Go to About"):
#         page_name = "About"

# # Content for each page
# if page_name == "Home":
#     st.title("Welcome to the Home Page")
#     st.write("This is the home page content.")
# elif page_name == "Data":
#     st.title("Data Page")
#     st.write("Here is where you can display data.")
# elif page_name == "About":
#     st.title("About Page")
#     st.write("This page contains information about the app.")

# # Define pages as separate functions
# def home():
#     st.title("Home Page")
#     st.write("Welcome to the Home Page!")

# def data():
#     st.title("Data Page")
#     st.write("Here is where you can display data.")

# def about():
#     st.title("About Page")
#     st.write("This page contains information about the app.")

# def authenticated_menu():
#     # Show a navigation menu for authenticated users
#     st.sidebar.page_link("app.py", label="Switch accounts")
#     st.sidebar.page_link("pages/user.py", label="Your profile")
#     if st.session_state.role in ["admin", "super-admin"]:
#         st.sidebar.page_link("pages/admin.py", label="Manage users")
#         st.sidebar.page_link(
#             "pages/super-admin.py",
#             label="Manage admin access",
#             disabled=st.session_state.role != "super-admin",
#         )


# def unauthenticated_menu():
#     # Show a navigation menu for unauthenticated users
#     st.sidebar.page_link("app.py", label="Log in")


# def menu():
#     # Determine if a user is logged in or not, then show the correct
#     # navigation menu
#     if "role" not in st.session_state or st.session_state.role is None:
#         unauthenticated_menu()
#         return
#     authenticated_menu()


# def menu_with_redirect():
#     # Redirect users to the main page if not logged in, otherwise continue to
#     # render the navigation menu
#     if "role" not in st.session_state or st.session_state.role is None:
#         st.switch_page("app.py")
#     menu()


@st.cache_data(ttl=3600, show_spinner="正在加載資料...")
def load_map(url):
    with open(url, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    return geojson_data
geojson_data = load_map('data/Tainan_County.geojson')

# 讀取 GeoJSON 文件內容
try:
    pass
except FileNotFoundError:
    st.error("GeoJSON file not found.")
else:
    selected_layers = [
    pdk.Layer(
        "GeoJsonLayer",
        geojson_data,  # 使用已加載的 GeoJSON 數據
        opacity=1.0,  # 設置為不透明
        stroked=True,
        filled=False,
        wireframe=True,
        get_line_color=[255, 0, 0],  # 紅色邊界
        get_line_width=80,  # 增加線條寬度
    )
]
    # 渲染地圖
    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state={
                "latitude": 23.13,
                "longitude": 120.312480,
                "zoom": 9,
                "pitch": 10,
            },
            layers=selected_layers,
        )
    )


