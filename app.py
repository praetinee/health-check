import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="ดูผลตรวจสุขภาพ", layout="centered")

# โหลด key จาก Streamlit Secrets
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# ดึงข้อมูลจาก Google Sheets
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1XmYIOdp6dxjQbfn17xhDLVwUMswgU_mwUYFlEX7rOgI")
worksheet = spreadsheet.sheet1
df = pd.DataFrame(worksheet.get_all_records())

st.title("🔎 ตรวจสอบผลสุขภาพของคุณ")
id_card = st.text_input("กรุณาใส่เลขบัตรประชาชน 13 หลัก")

if id_card:
    result = df[df['เลขบัตรประชาชน'] == id_card]

    if not result.empty:
        st.success(f"ข้อมูลของคุณ: {result.iloc[0]['ชื่อ-สกุล']}")
        st.dataframe(result.T)
    else:
        st.error("❌ ไม่พบข้อมูลในระบบ กรุณาตรวจสอบเลขบัตรประชาชนอีกครั้ง")
