import streamlit as st
import pandas as pd
import gspread
import json
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials

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

required_columns = ['เลขบัตรประชาชน', 'HN', 'ชื่อ-สกุล']
if not all(col in df.columns for col in required_columns):
    st.error("❌ โครงสร้างข้อมูลผิด กรุณาตรวจสอบ Google Sheet")
    st.stop()

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
    except (ValueError, TypeError):
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
    except (ValueError, TypeError):
        return "-"

def assess_waist(waist):
    try:
        waist = float(waist)
        return "เกินเกณฑ์" if waist > 90 else "ปกติ"
    except (ValueError, TypeError):
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
    query = df.copy()

    if id_card.strip():
        query = query[query["เลขบัตรประชาชน"] == id_card.strip()]
    if hn.strip():
        query = query[query["HN"] == hn.strip()]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
    elif len(query) > 1:
        st.warning("🔎 พบหลายรายการที่ตรงกัน กรุณาระบุให้ชัดเจนขึ้น")
        st.dataframe(query)
        st.stop()
    else:
        st.session_state["person_records"] = query

# ===============================
# DISPLAY RESULTS
# ===============================
if "person_records" in st.session_state:
    person_df = st.session_state["person_records"]
    person_info = person_df.iloc[0]

    # Header line
    line_info = f"""
    ✅ พบข้อมูลของ: **{person_info.get('ชื่อ-สกุล', '-')}**  
    🆔 {person_info.get('เลขบัตรประชาชน', '-')} | HN: {person_info.get('HN', '-')} | เพศ: {person_info.get('เพศ', '-')}
    """
    st.markdown(line_info)

    # Health info by year
    st.markdown("### 📊 น้ำหนัก / ส่วนสูง / รอบเอว")

    if "ปี" not in person_df.columns:
        st.warning("ไม่พบคอลัมน์ 'ปี' กรุณาตรวจสอบ Google Sheet ว่ามีปีระบุหรือไม่")
    else:
        person_df = person_df.sort_values(by="ปี", ascending=False)
        for _, row in person_df.iterrows():
            year = int(row.get("ปี", 0))
            weight = row.get("น้ำหนัก")
            height = row.get("ส่วนสูง")
            waist = row.get("รอบเอว")
            sbp = row.get("SBP", 0)
            dbp = row.get("DBP", 0)
            pulse = row.get("ชีพจร", "-")
            bmi = calc_bmi(weight, height)

            st.markdown(f"#### 🗓 ปี {year + 543}")
            st.write(f"- น้ำหนัก: {weight} กก.")
            st.write(f"- ส่วนสูง: {height} ซม.")
            st.write(f"- รอบเอว: {waist} ซม. ({assess_waist(waist)})")
            st.write(f"- BMI: {bmi} ({interpret_bmi(bmi)})")
            st.write(f"- ความดัน: {sbp}/{dbp} mmHg ({interpret_bp(sbp, dbp)})")
            st.write(f"- ชีพจร: {pulse} ครั้ง/นาที")
