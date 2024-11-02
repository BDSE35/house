import streamlit as st
def menu():
    # Show a navigation menu for authenticated users
    st.sidebar.page_link("app.py", label="首頁")
    st.sidebar.page_link("pages/Southern_Taiwan_Science_Park.py", label="南科園區指標") # Southern Taiwan Science Park

    with st.sidebar.expander("南科聚落", expanded=True):
            st.page_link("pages/DBSCAN.py", label="聚落分布", icon="🔐")
            st.page_link("pages/KDE.py", label="交易密度", icon="👤")
            
    
    with st.sidebar.expander("房價特徵權重變化趨勢", expanded=True):
            st.page_link("pages/RF_all.py", label="Random Forest", icon="👤")
            st.page_link("pages/XG_all.py", label="XGboost", icon="🔐")
            

    # with st.sidebar.expander("房價權重變化趨勢", expanded=True):
    #     section2 = st.radio("", ["總體", "南科聚落"])
    #     if section2 == "總體":
    #         st.sidebar.page_link("pages/RF_all.py", label="Random Forest", icon="👤")
    #         st.sidebar.page_link("pages/XG_all.py", label="XGboost", icon="🔐")
    #     elif section2 == "南科聚落":
    #         st.sidebar.page_link("pages/streamlit_app.py", label="Random Forest", icon="🏢")
    #         st.sidebar.page_link("pages/streamlit_app.py", label="XGboost", icon="🔐")
    st.sidebar.page_link("pages/LSTM.py", label="房價預測")
