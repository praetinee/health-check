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

# เปลี่ยน URL ตามไฟล์ใหม่ที่คุณใช้
sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
spreadsheet = client.open_by_url(sheet_url)
worksheet = spreadsheet.sheet1
df = pd.DataFrame(worksheet.get_all_records())

# ล้างช่องว่างในชื่อคอลัมน์เพื่อให้ตรงกับชื่อจริง
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str)
df['HN'] = df['HN'].astype(str)
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str)

# ===============================
# SEARCH UI
# ===============================
st.markdown("<h1 style='text-align:center;'>🔍 ตรวจสอบผลสุขภาพของคุณ</h1>", unsafe_allow_html=True)

# ช่องกรอกข้อมูลแนวนอน
col1, col2, col3 = st.columns(3)
with col1:
    id_card = st.text_input("เลขบัตรประชาชน", placeholder="เช่น 1234567890123")
with col2:
    hn = st.text_input("HN", placeholder="เช่น 012345")
with col3:
    full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี")

# ปุ่มค้นหา (อยู่นอก columns)
if st.button("ค้นหา"):
    result = pd.DataFrame()

    if id_card.strip():
        result = df[df["เลขบัตรประชาชน"] == id_card.strip()]
    elif hn.strip():
        result = df[df["HN"] == hn.strip()]
    elif full_name.strip():
        result = df[df["ชื่อ-สกุล"] == full_name.strip()]

    if result.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.write("🔎 ลองตรวจสอบชื่อคอลัมน์ใน Google Sheets และชื่อ-นามสกุล หรือ HN อีกครั้ง")
    else:
        person = result.iloc[0]
        st.success(f"✅ พบข้อมูลของ {person.get('ชื่อ-สกุล', '-')}")
        st.markdown(f"""
        **HN:** {person.get('HN', '-')}  
        **เลขบัตรประชาชน:** {person.get('เลขบัตรประชาชน', '-')}  
        **เพศ:** {person.get('เพศ', '-')}  
        **อายุ:** {person.get('อายุ', '-')}  
        """)
        st.dataframe(person.to_frame().T, use_container_width=True)
