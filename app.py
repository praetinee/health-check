import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# PAGE CONFIG + FONTS
# ===============================
st.set_page_config(page_title="ตรวจสอบผลสุขภาพ", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun&display=swap');
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================
# LOAD GOOGLE SHEETS
# ===============================
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
spreadsheet = client.open_by_url(sheet_url)
worksheet = spreadsheet.sheet1
df = pd.DataFrame(worksheet.get_all_records())
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str)
df['HN'] = df['HN'].astype(str)
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str)

# ===============================
# HEADER
# ===============================
st.markdown("""
<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>
<h4 style='text-align:center; color:gray;'>- กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>
""", unsafe_allow_html=True)

# ===============================
# SEARCH FORM
# ===============================
with st.form("search_form", clear_on_submit=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        citizen_id = st.text_input("เลขบัตรประชาชน", placeholder="เช่น 1234567890123", key="cid")
    with col2:
        hn = st.text_input("HN", placeholder="เช่น 123456", key="hn")
    with col3:
        full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี", key="fname")

    submitted = st.form_submit_button("ตรวจสอบ")

if submitted:
    result = pd.DataFrame()
    if citizen_id.strip():
        result = df[df['เลขบัตรประชาชน'] == citizen_id.strip()]
    elif hn.strip():
        result = df[df['HN'] == hn.strip()]
    elif full_name.strip():
        result = df[df['ชื่อ-สกุล'].str.strip() == full_name.strip()]

    if result.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
    else:
        person = result.iloc[0]
        st.success(f"✅ พบข้อมูลของ: {person.get('ชื่อ-สกุล', '-')}")
        st.markdown(f"**HN:** {person.get('HN', '-')}  ")
        st.markdown(f"**เลขบัตรประชาชน:** {person.get('เลขบัตรประชาชน', '-')}  ")
        st.markdown(f"**เพศ:** {person.get('เพศ', '-')}  ")
        st.dataframe(person.to_frame().T, use_container_width=True)

# ===============================
# ส่วนแสดงผลสุขภาพตามปีที่เลือก
# ===============================

st.markdown("### 📅 เลือกปี พ.ศ. ที่ต้องการดูผลสุขภาพ")
selected_year_display = st.selectbox("เลือกปี", [f"พ.ศ. 25{y}" for y in range(61, 69)])
selected_year = selected_year_display[-2:]  # ดึงเลขปี เช่น '68'

# ดึงข้อมูลจากปีที่เลือก
def get_value(field_prefix):
    return person.get(f"{field_prefix}{selected_year}", "-")

weight = get_value("น้ำหนัก")
height = get_value("ส่วนสูง")
waist = get_value("รอบเอว")
sbp = get_value("SBP")
dbp = get_value("DBP")
pulse = get_value("pulse")

# คำนวณ BMI
bmi_value = calc_bmi(weight, height)
bmi_text = f"{bmi_value:.1f}" if bmi_value else "-"
bmi_result = interpret_bmi(bmi_value)

# แปลผลความดัน
bp_text = f"{sbp}/{dbp}" if sbp != "-" and dbp != "-" else "-"
bp_result = interpret_bp(sbp, dbp)

# ประเมินรอบเอว (เกณฑ์ 90 cm เป็นค่า default)
waist_result = assess_waist(waist)

# แสดงผลลัพธ์
st.markdown("### 🧍‍♂️ ข้อมูลทั่วไป (เฉพาะปีที่เลือก)")
data_summary = pd.DataFrame({
    "น้ำหนัก (กก.)": [weight],
    "ส่วนสูง (ซม.)": [height],
    "รอบเอว (ซม.)": [waist],
    "BMI": [bmi_text],
    "แปลผล BMI": [bmi_result or "-"],
    "ค่าความดัน (mmHg)": [bp_text],
    "แปลผลความดัน": [bp_result or "-"],
    "แปลผลรอบเอว": [waist_result or "-"],
    "ชีพจร (bpm)": [pulse]
})
st.dataframe(data_summary.T.rename(columns={0: selected_year_display}), use_container_width=True)
