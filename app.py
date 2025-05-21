
import streamlit as st
import pandas as pd
import gspread
import json
import re
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# PAGE CONFIG + FONTS
# ===============================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
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
# FUNCTIONS
# ===============================
def calc_bmi(weight, height):
    try:
        weight = float(weight)
        height = float(height)
        return round(weight / ((height / 100) ** 2), 1)
    except:
        return None

def interpret_bmi(bmi):
    if bmi is None:
        return "-"
    if bmi > 30:
        return "อ้วนมาก"
    elif bmi >= 25:
        return "อ้วน"
    elif bmi >= 23:
        return "น้ำหนักเกิน"
    elif bmi >= 18.5:
        return "ปกติ"
    else:
        return "ผอม"

def interpret_bp(sbp, dbp):
    try:
        sbp = float(sbp)
        dbp = float(dbp)
        if sbp == 0 or dbp == 0:
            return "-"
        if sbp >= 160 or dbp >= 100:
            return "ความดันโลหิตสูง"
        elif sbp >= 140 or dbp >= 90:
            return "ความดันโลหิตสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80:
            return "ความดันโลหิตปกติ"
        else:
            return "ความดันโลหิตปกติค่อนข้างสูง"
    except:
        return "-"

def assess_waist(waist):
    try:
        waist = float(waist)
        return "เกินเกณฑ์" if waist > 90 else "ปกติ"
    except:
        return "-"

# ===============================
# HEADER & FORM
# ===============================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        id_card = st.text_input("เลขบัตรประชาชน")
    with col2:
        hn = st.text_input("HN")
    with col3:
        full_name = st.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ตรวจสอบ")

if submitted:
    person = None
    if id_card.strip():
        result = df[df["เลขบัตรประชาชน"] == id_card.strip()]
    elif hn.strip():
        result = df[df["HN"] == hn.strip()]
    elif full_name.strip():
        result = df[df["ชื่อ-สกุล"].str.strip() == full_name.strip()]
    else:
        result = pd.DataFrame()

    if result.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
    else:
        person = result.iloc[0].to_dict()
        st.session_state["person_data"] = person

        # =====================================
        # ✅ คำนวณ available_years_sorted ที่นี่
        # =====================================
        available_years_sorted = []
        for y in range(61, 69):
            urine_key = f"ผลปัสสาวะ{y}" if y < 68 else "ผลปัสสาวะ"
            extra_fields = [f"ผลเอกซเรย์{y}", f"วัคซีน{y}", f"ตรวจตา{y}"]
            if any([
                person.get(f"น้ำหนัก{y}"),
                person.get(f"ส่วนสูง{y}"),
                person.get(f"รอบเอว{y}"),
                person.get(f"SBP{y}"),
                person.get(f"DBP{y}"),
                person.get(f"pulse{y}"),
                person.get(urine_key),
                *[person.get(field) for field in extra_fields]
            ]):
                available_years_sorted.append(y)
        available_years_sorted = sorted(available_years_sorted)
        st.session_state["available_years_sorted"] = available_years_sorted

# ===============================
# DISPLAY RESULTS
# ===============================
if "person_data" in st.session_state:
    person = st.session_state["person_data"]
    available_years_sorted = st.session_state.get("available_years_sorted", [])

    st.success(f"✅ พบข้อมูลของ: {person['ชื่อ-สกุล']}")
    st.markdown(f"**HN:** {person['HN']}  
**เลขบัตรประชาชน:** {person['เลขบัตรประชาชน']}  
**เพศ:** {person.get('เพศ', '-')}")

    if available_years_sorted:
        year_display = {f"พ.ศ. 25{y}": y for y in available_years_sorted}
        selected_label = st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผล", list(year_display.keys()))
        selected_year = year_display[selected_label]

        # ดำเนินการต่อที่บล็อกวิเคราะห์สุขภาพ และปัสสาวะ...
    else:
        st.warning("ไม่พบปีที่มีข้อมูล")
