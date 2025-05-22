import streamlit as st
import pandas as pd
from data_loader import load_data
from config import years, columns_by_year
from bmi_utils import interpret_bmi, interpret_bp
from urine_interpret import (
    interpret_alb, interpret_sugar, interpret_rbc, interpret_wbc,
    summarize_urine, advice_urine
)

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
