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

# Clean column names
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str)
df['HN'] = df['HN'].astype(str)
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str)

# ===============================
# SEARCH FORM (unchanged)
# ===============================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

with st.form(key="search_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        citizen_id = st.text_input("เลขบัตรประชาชน", max_chars=13, placeholder="เช่น 1234567890123")
    with col2:
        hn = st.text_input("HN", placeholder="เช่น 123456")
    with col3:
        full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี")
    submitted = st.form_submit_button("ตรวจสอบ")

if submitted:
    matched = df[
        (df["เลขบัตรประชาชน"] == citizen_id.strip()) |
        (df["HN"] == hn.strip()) |
        (df["ชื่อ-สกุล"].str.strip() == full_name.strip())
    ]

    if matched.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
    else:
        person = matched.iloc[0]
        st.success(f"✅ พบข้อมูลของ {person.get('ชื่อ-สกุล', '-')}")
        st.markdown(f"**HN:** {person.get('HN', '-')}  ")
        st.markdown(f"**เลขบัตรประชาชน:** {person.get('เลขบัตรประชาชน', '-')}  ")
        st.markdown(f"**เพศ:** {person.get('เพศ', '-')}")

        # ===============================
        # YEAR SELECTION
        # ===============================
        year_map = {"2561": "61", "2562": "62", "2563": "63", "2564": "64", "2565": "65", "2566": "66", "2567": "67", "2568": "68"}
        selected_year = st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผลตรวจ", list(year_map.keys()), index=7)
        y = year_map[selected_year]

        def safe_get(field):
            return person.get(f"{field}{y}", "-")

        weight = safe_get("น้ำหนัก")
        height = safe_get("ส่วนสูง")
        waist = safe_get("รอบเอว")
        sbp = safe_get("SBP")
        dbp = safe_get("DBP")
        pulse = safe_get("pulse")

        # คำนวณ BMI
        try:
            bmi = round(float(weight) / ((float(height)/100)**2), 1)
        except:
            bmi = "-"

        if isinstance(bmi, float):
            if bmi > 30:
                bmi_result = "อ้วนมาก"
            elif bmi >= 25:
                bmi_result = "อ้วน"
            elif bmi >= 23:
                bmi_result = "น้ำหนักเกิน"
            elif bmi >= 18.5:
                bmi_result = "ปกติ"
            else:
                bmi_result = "ผอม"
        else:
            bmi_result = "-"

        # ความดันโลหิต
        try:
            sbp_f, dbp_f = float(sbp), float(dbp)
            if sbp_f == 0 or dbp_f == 0:
                bp_result = "-"
            elif sbp_f >= 160 or dbp_f >= 100:
                bp_result = "ความดันโลหิตสูง"
            elif sbp_f >= 140 or dbp_f >= 90:
                bp_result = "ความดันโลหิตสูงเล็กน้อย"
            elif sbp_f < 120 and dbp_f < 80:
                bp_result = "ความดันโลหิตปกติ"
            else:
                bp_result = "ความดันโลหิตปกติค่อนข้างสูงเล็กน้อย"
        except:
            bp_result = "-"

        # รอบเอว
        try:
            waist = float(waist)
            gender = person.get("เพศ", "")
            waist_threshold = 90 if gender == "ชาย" else 80
            waist_result = "เกินเกณฑ์" if waist > waist_threshold else "ปกติ"
        except:
            waist_result = "-"

        # ===============================
        # DISPLAY SUMMARY
        # ===============================
        st.markdown("### 📋 ผลตรวจปี " + selected_year)
        summary = pd.DataFrame({
            "รายการ": ["น้ำหนัก (กก.)", "ส่วนสูง (ซม.)", "รอบเอว (ซม.)", "BMI", "แปลผล BMI", "ความดัน (mmHg)", "แปลผลความดัน", "ชีพจร (ครั้ง/นาที)", "แปลผลรอบเอว"],
            "ค่า": [weight, height, waist, bmi, bmi_result, f"{sbp}/{dbp}", bp_result, pulse, waist_result]
        })
        st.dataframe(summary.set_index("รายการ"), use_container_width=True)
