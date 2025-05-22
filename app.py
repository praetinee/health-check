import streamlit as st
from data_loader import load_data
from config import years, columns_by_year
from bmi_utils import interpret_bmi, interpret_bp
from urine_interpret import (
    interpret_alb, interpret_sugar, interpret_rbc, interpret_wbc,
    summarize_urine, advice_urine
)

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# โหลดข้อมูล
df = load_data()

# คุณสามารถใส่โค้ด form + แสดงผลเดิมที่อยู่ใน app_backup.py ต่อจากนี้ได้
st.title("ระบบรายงานสุขภาพ")
st.write("เริ่มต้นใช้งานแล้ว ✅")
