# 📁 app.py

import streamlit as st
from core_ui import render_ui
from data_loader import load_data
from config import years, columns_by_year

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch&display=swap');
    html, body, [class*="css"] {
        font-family: 'Chakra Petch', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

df = load_data()
render_ui(df)
