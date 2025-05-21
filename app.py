import numpy as np
import streamlit as st
import pandas as pd
import gspread
import json
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch&display=swap');

    html, body, [class*="css"] {
        font-family: 'Chakra Petch', sans-serif !important;
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

    # ✅ แสดงชื่อคนไข้ ด้วยแถบเขียว และขนาดใหญ่
    # ✅ ปลอดภัย ไม่ทำให้ error
    st.success(f"✅ พบข้อมูลของ: {person.get('ชื่อ-สกุล', '-')}")

    # ✅ แสดงเลขบัตร / HN / เพศ ด้วยสีขาว (เพื่อ contrast กับพื้นเข้ม)
    st.markdown(f"""
    <p style='color: white; font-size: 16px; line-height: 1.6;'>
    เลขบัตรประชาชน: {person.get('เลขบัตรประชาชน', '-')}<br>
    HN: {person.get('HN', '-')}<br>
    เพศ: {person.get('เพศ', '-')}
    </p>
    """, unsafe_allow_html=True)

    # ✅ สร้างตารางข้อมูลสุขภาพตามปี
    table_data = {
        "ปี พ.ศ.": [],
        "น้ำหนัก (กก.)": [],
        "ส่วนสูง (ซม.)": [],  # ✅ เพิ่มตรงนี้
        "รอบเอว (ซม.)": [],
        "ความดัน (mmHg)": [],
        "BMI (แปลผล)": []
    }


    for y in sorted(years):
        cols = columns_by_year[y]  # ✅ ต้องมี
        weight = person.get(cols["weight"], "")
        height = person.get(cols["height"], "")
        waist = person.get(cols["waist"], "")
        sbp = person.get(cols["sbp"], "")
        dbp = person.get(cols["dbp"], "")

        # ✅ คำนวณ BMI จากน้ำหนักและส่วนสูง
        try:
            bmi_val = float(weight) / ((float(height) / 100) ** 2)
            bmi_val = round(bmi_val, 1)
            bmi_str = f"{bmi_val}<br><span style='font-size: 13px; color: gray;'>{interpret_bmi(bmi_val)}</span>"
        except:
            bmi_val = None
            bmi_str = "-"

        # ✅ แปลผลความดัน
        try:
            if sbp or dbp:
                bp_val = f"{sbp}/{dbp}"
                bp_meaning = interpret_bp(sbp, dbp)
                bp_str = f"{bp_val}<br><span style='font-size: 13px; color: gray;'>{bp_meaning}</span>"
            else:
                bp_str = "-"
        except:
            bp_str = "-"

        # ✅ เติมข้อมูลลงตาราง
        table_data["ปี พ.ศ."].append(y + 2500)
        table_data["น้ำหนัก (กก.)"].append(weight if weight else "-")
        table_data["ส่วนสูง (ซม.)"].append(height if height else "-")
        table_data["รอบเอว (ซม.)"].append(waist if waist else "-")
        table_data["ความดัน (mmHg)"].append(bp_str)
        table_data["BMI (แปลผล)"].append(bmi_str)

    # ✅ แสดงผลตาราง (รองรับ HTML <br> ด้วย unsafe_allow_html)
    st.markdown("### 📊 น้ำหนัก / รอบเอว / ความดัน")
    html_table = pd.DataFrame(table_data).set_index("ปี พ.ศ.").T.to_html(escape=False)
    st.markdown(html_table, unsafe_allow_html=True)

# ==========================
# GRAPH: BMI History
# ==========================

bmi_data = []
labels = []

for y in sorted(years):
    cols = columns_by_year[y]  # ✅ ต้องมีตรงนี้ก่อนใช้ cols

    weight = person.get(cols["weight"], "")
    height = person.get(cols["height"], "")
    
    try:
        weight = float(weight)
        height = float(height)
        bmi_val = round(weight / ((height / 100) ** 2), 1)
        bmi_data.append(bmi_val)
        labels.append(f"B.E. {y + 2500}")
    except:
        continue

    # ✅ วาดกราฟถ้ามีข้อมูล
if bmi_data and labels:
    st.markdown("### 📈 BMI Trend")
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.axhspan(0, 18.5, facecolor='#4285F4', alpha=0.3, label='Underweight')
    ax.axhspan(18.5, 23, facecolor='#34A853', alpha=0.3, label='Normal')
    ax.axhspan(23, 25, facecolor='#FBBC05', alpha=0.4, label='Overweight')
    ax.axhspan(25, 30, facecolor='#FF8800', alpha=0.4, label='Obese')
    ax.axhspan(30, 40, facecolor='#EA4335', alpha=0.4, label='Severely Obese')

    ax.plot(np.arange(len(labels)), bmi_data, marker='o', color='black', label="BMI")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("BMI")
    ax.set_ylim(15, 40)
    ax.set_title("BMI Over Time")
    ax.legend(loc="upper left")

    st.pyplot(fig)
else:
    st.info("ไม่มีข้อมูล BMI เพียงพอสำหรับแสดงกราฟ")
