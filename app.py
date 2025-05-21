import streamlit as st

# ====================
# USER AUTH
# ====================
USERS = {
    "admin": "1234",
    "nurse": "nursepass",
    "doctor": "drpass"
}

def login():
    st.title("🔐 เข้าสู่ระบบรายงานผลสุขภาพ")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if username in USERS and USERS[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.experimental_rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

def logout():
    st.session_state.clear()
    st.experimental_rerun()

# ====================
# GUARD
# ====================
if "logged_in" not in st.session_state:
    login()
    st.stop()
else:
    st.sidebar.success(f"👤 คุณ: {st.session_state['user']}")
    if st.sidebar.button("ออกจากระบบ"):
        logout()

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
# CONNECT GOOGLE SHEET
# ===============================
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
worksheet = client.open_by_url(sheet_url).sheet1
df = pd.DataFrame(worksheet.get_all_records())
df.columns = df.columns.str.strip()

# ===============================
# YEAR MAPPING
# ===============================
years = list(range(61, 69))
columns_by_year = {
    year: {
        "weight": f"น้ำหนัก{year}" if year != 68 else "น้ำหนัก",
        "height": f"ส่วนสูง{year}" if year != 68 else "ส่วนสูง",
        "waist": f"รอบเอว{year}" if year != 68 else "รอบเอว",
        "sbp": f"SBP{year}" if year != 68 else "SBP",
        "dbp": f"DBP{year}" if year != 68 else "DBP",
        "pulse": f"pulse{year}" if year != 68 else "pulse",
        "bmi_value": f"BMI{year}" if year != 68 else "ดัชนีมวลกาย",
    }
    for year in years
}

# ===============================
# FUNCTIONS
# ===============================
def interpret_bmi(bmi):
    if bmi is None or bmi == "":
        return "-"
    try:
        bmi = float(bmi)
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
    except:
        return "-"

def interpret_waist(waist, height):
    try:
        waist = float(waist)
        height = float(height)
        return "เกินเกณฑ์" if waist > height else "ปกติ"
    except:
        return "-"

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

# ===============================
# UI SEARCH
# ===============================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")

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

# ===============================
# DISPLAY
# ===============================
if "person" in st.session_state:
    person = st.session_state["person"]
    st.success(f"✅ พบข้อมูลของ: **{person.get('ชื่อ-สกุล', '-')}**")
    st.markdown(f"""
        🆔 {person.get('เลขบัตรประชาชน', '-')} | HN: {person.get('HN', '-')} | เพศ: {person.get('เพศ', '-')}
    """)

    selected_year = st.selectbox("เลือกปี พ.ศ.", sorted([y + 2500 for y in years], reverse=True))
    year = selected_year - 2500
    cols = columns_by_year.get(year, {})

    weight = person.get(cols["weight"], "")
    height = person.get(cols["height"], "")
    waist = person.get(cols["waist"], "")
    sbp = person.get(cols["sbp"], "")
    dbp = person.get(cols["dbp"], "")
    pulse = person.get(cols["pulse"], "")
    bmi = person.get(cols["bmi_value"], "")

    st.markdown(f"### 📊 ผลตรวจสุขภาพ ปี {selected_year}")
    st.write(f"- น้ำหนัก: {weight} กก.")
    st.write(f"- ส่วนสูง: {height} ซม.")
    st.write(f"- รอบเอว: {waist} ซม. ({interpret_waist(waist, height)})")
    st.write(f"- BMI: {bmi} ({interpret_bmi(bmi)})")
    st.write(f"- ความดัน: {sbp}/{dbp} mmHg ({interpret_bp(sbp, dbp)})")
    st.write(f"- ชีพจร: {pulse} ครั้ง/นาที")

    # ==========================
    # GRAPH: BMI + Waist History
    # ==========================
    bmi_data = []
    waist_data = []
    labels = []

    for y in sorted(years):
        col = columns_by_year[y]
        try:
            bmi_val = float(person.get(col["bmi_value"], 0))
            waist_val = float(person.get(col["waist"], 0))
            if bmi_val > 0:
                bmi_data.append(bmi_val)
                waist_data.append(waist_val)
                labels.append(f"B.E. {y + 2500}")
        except:
            continue

    if bmi_data:
        st.markdown("### 📈 BMI Trend")
        fig, ax = plt.subplots()
        ax.plot(labels, bmi_data, marker='o', label="BMI")
        ax.set_ylabel("BMI")
        ax.set_title("BMI Over Time")
        ax.legend()
        st.pyplot(fig)

    if waist_data:
        st.markdown("### 📈 Waist Circumference Trend")
        fig, ax = plt.subplots()
        ax.plot(labels, waist_data, marker='o', label="Waist (cm)")
        ax.set_ylabel("Waist (cm)")
        ax.set_title("Waist Circumference Over Time")
        ax.legend()
        st.pyplot(fig)
