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
        st.session_state["person_data"] = result.iloc[0].to_dict()

# ===============================
# DISPLAY RESULTS
# ===============================
if "person_data" in st.session_state:
    person = st.session_state["person_data"]
    st.success(f"✅ พบข้อมูลของ: {person['ชื่อ-สกุล']}")
    st.markdown(f"**HN:** {person['HN']}  \n**เลขบัตรประชาชน:** {person['เลขบัตรประชาชน']}  \n**เพศ:** {person.get('เพศ', '-')}")

    available_years = sorted(set(
        int(re.search(r'(\d{2})$', col).group(1)) 
        for col in df.columns 
        if re.search(r'น้ำหนัก\d{2}$', col)
    ), reverse=True)

    year_display = {f"พ.ศ. 25{y}": y for y in available_years}
    selected_label = st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผล", list(year_display.keys()))
    selected_year = year_display[selected_label]

    # ข้อมูลรายปี
    weight = person.get(f"น้ำหนัก{selected_year}", "-")
    height = person.get(f"ส่วนสูง{selected_year}", "-")
    waist = person.get(f"รอบเอว{selected_year}", "-")
    sbp = person.get(f"SBP{selected_year}", "-")
    dbp = person.get(f"DBP{selected_year}", "-")
    pulse = person.get(f"pulse{selected_year}", "-")
    bmi = calc_bmi(weight, height)
    bmi_text = f"{bmi:.1f}" if bmi else "-"

    st.markdown("### 📋 ข้อมูลสุขภาพประจำปี")
    st.markdown(f"""
    - **ปี พ.ศ.**: 25{selected_year}  
    - **น้ำหนัก:** {weight} กก.  
    - **ส่วนสูง:** {height} ซม.  
    - **รอบเอว:** {waist} ซม. ({assess_waist(waist)})  
    - **BMI:** {bmi_text} ({interpret_bmi(bmi)})  
    - **ความดันโลหิต:** {sbp}/{dbp} mmHg ({interpret_bp(sbp, dbp)})  
    - **ชีพจร:** {pulse} ครั้ง/นาที
    """)

    # ===============================
    # สรุปสุขภาพแบบ Transpose
    # ===============================
    summary_data = {}
    for y in available_years:
        summary_data[f"25{y}"] = {
            "น้ำหนัก (กก.)": person.get(f"น้ำหนัก{y}", "-"),
            "ส่วนสูง (ซม.)": person.get(f"ส่วนสูง{y}", "-"),
            "รอบเอว (ซม.)": person.get(f"รอบเอว{y}", "-"),
            "BMI": calc_bmi(person.get(f"น้ำหนัก{y}", "-"), person.get(f"ส่วนสูง{y}", "-")),
            "ความดัน": f"{person.get(f'SBP{y}', '-')}/{person.get(f'DBP{y}', '-')}",
            "ชีพจร": person.get(f"pulse{y}", "-")
        }

    summary_df = pd.DataFrame(summary_data)
    st.markdown("### 📊 สรุปผลสุขภาพรายปี (แนวนอน)")
    st.dataframe(summary_df)

    # ===============================
    # กราฟแนวโน้ม BMI (เรียงปีจากน้อยไปมาก + สีเข้ม)
    # ===============================
    st.markdown("### 📈 BMI Trend Over Years")

    # เรียงปีจากน้อยไปมาก
    available_years_sorted = sorted(available_years)

    # สร้างข้อมูลตามปีที่เรียงแล้ว
    bmi_values = [
        calc_bmi(person.get(f"น้ำหนัก{y}", "-"), person.get(f"ส่วนสูง{y}", "-"))
        for y in available_years_sorted
    ]
    years_labels = [f"25{y}" for y in available_years_sorted]

    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot ค่า BMI
    ax.plot(years_labels, bmi_values, marker='o', linestyle='-', color='blue')

    # ====== โซนสีเข้มตามระดับ BMI ======
    ax.axhspan(0, 18.5, facecolor='#66ccff', alpha=0.6, label='Underweight')
    ax.axhspan(18.5, 23, facecolor='#66ff66', alpha=0.6, label='Normal')
    ax.axhspan(23, 25, facecolor='#ffff66', alpha=0.6, label='Overweight')
    ax.axhspan(25, 30, facecolor='#ff9933', alpha=0.6, label='Obese')
    ax.axhspan(30, 100, facecolor='#ff6666', alpha=0.6, label='Severely Obese')

    # ====== ตั้งค่ากราฟ ======
    ax.set_title("BMI Trend")
    ax.set_xlabel("Year (B.E.)")
    ax.set_ylabel("BMI")
    ax.set_ylim(bottom=15, top=max(bmi_values + [30]) + 2)
    ax.legend(loc='upper right')

    st.pyplot(fig)

