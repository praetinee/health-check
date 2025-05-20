import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# PAGE CONFIG + FONTS
# ===============================
st.set_page_config(page_title="ระบบรายงานผลตรวจสุขภาพ", layout="wide")
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

# ล้างช่องว่างหัวตาราง และแปลงข้อมูล
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
# SEARCH INPUTS
# ===============================
col1, col2, col3 = st.columns(3)
with col1:
    citizen_id = st.text_input("เลขบัตรประชาชน", placeholder="เช่น 1234567890123")
with col2:
    hn = st.text_input("HN", placeholder="เช่น 123456")
with col3:
    full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี")

# ===============================
# SEARCH ACTION
# ===============================
if st.button("ตรวจสอบ"):
    if not (citizen_id.strip() or hn.strip() or full_name.strip()):
        st.warning("⚠️ กรุณากรอกอย่างน้อยหนึ่งช่องเพื่อค้นหา")
    else:
        matched = df[
            (df['เลขบัตรประชาชน'] == citizen_id.strip()) |
            (df['HN'] == hn.strip()) |
            (df['ชื่อ-สกุล'].str.contains(full_name.strip(), case=False, na=False))
        ]

        if matched.empty:
            st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        else:
            person = matched.iloc[0]
            st.success("✅ พบข้อมูล: สมบูรณ์ วันที่ดี")
            st.markdown(f"**เพศ:** {person.get('เพศ', '-')}\n")

            # ตัวอย่างแสดงผล: น้ำหนัก/รอบเอว/ความดัน (แค่ตัวอย่าง)
            st.markdown("### 🧬 น้ำหนัก/รอบเอว/ความดัน")
            years = list(range(61, 64))  # เปลี่ยนตามปีที่มีจริงในชีท
            display_years = [f"พ.ศ. 25{y}" for y in years]

            def get_values(prefix):
                return [person.get(f"{prefix}{y}", "-") for y in years]

            weights = get_values("น้ำหนัก")
            heights = get_values("ส่วนสูง")
            waists = get_values("รอบเอว")

            summary_df = pd.DataFrame({
                "ปี พ.ศ.": display_years,
                "น้ำหนัก (กก.)": weights,
                "ส่วนสูง (ซม.)": heights,
                "รอบเอว (ซม.)": waists
            })

            st.dataframe(summary_df.set_index("ปี พ.ศ.").T, use_container_width=True)
