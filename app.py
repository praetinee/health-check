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

with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")  # ✅ สร้างตัวแปรตรงนี้เท่านั้น!

# ✅ หลังจาก form เสร็จแล้ว ถึงใช้ได้
if submitted:
    query = df.copy()
    if id_card.strip():
        query = query[query["เลขบัตรประชาชน"] == id_card.strip()]
    if hn.strip():
        query = query[query["HN"] == hn.strip()]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
    else:
        st.session_state["person"] = query.iloc[0]

            if "person" in st.session_state:
                person = st.session_state["person"]
                st.success(f"✅ พบข้อมูลของ: {person.get('ชื่อ-สกุล', '-')}")

