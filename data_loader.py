import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

def load_data():
    try:
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        client = gspread.authorize(creds)

        sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
        worksheet = client.open_by_url(sheet_url).sheet1

        raw_data = worksheet.get_all_records()
        if not raw_data:
            st.error("❌ ไม่พบข้อมูล")
            st.stop()

        df = pd.DataFrame(raw_data)
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        df['HN'] = df['HN'].astype(str).str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        return df

    except Exception as e:
        st.error(f"โหลดข้อมูลล้มเหลว: {e}")
        st.stop()

