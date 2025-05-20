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

# ===============================
# 💧รายงานผลปัสสาวะประจำปี (พร้อมแปลผล + คำแนะนำ)
# ===============================

urine_key = f"ผลปัสสาวะ{selected_year}" if selected_year < 68 else "ผลปัสสาวะ"
urine_result = person.get(urine_key, "").strip()

alb_raw = person.get("Alb", "").strip()
sugar_raw = person.get("sugar", "").strip()
rbc_raw = person.get("RBC1", "").strip()
wbc_raw = person.get("WBC1", "").strip()

# === ฟังก์ชันแปลผล ===
def translate_alb(value):
    if value == "":
        return "-"
    v = value.lower()
    if v == "negative":
        return "ไม่พบโปรตีนในปัสสาวะ"
    elif v in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif v == "3+":
        return "พบโปรตีนในปัสสาวะ"
    return "-"

def translate_sugar(value):
    if value == "":
        return "-"
    v = value.lower()
    if v == "negative":
        return "ไม่พบน้ำตาลในปัสสาวะ"
    elif v == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif v in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสสาวะ"
    return "-"

def translate_rbc(value):
    if value == "":
        return "-"
    v = value.lower()
    if v in ["negative", "0-1", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif v in ["5-10", "10-20"]:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"

def translate_wbc(value):
    if value == "":
        return "-"
    v = value.lower()
    if v in ["negative", "0-1", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif v in ["5-10", "10-20"]:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"

# === ฟังก์ชันคำแนะนำ ===
def urine_advice_interpret(sex, alb_text, sugar_text, rbc_text, wbc_text, urine_result):
    if urine_result == "":
        return ""

    if urine_result == "ปัสสาวะปกติ":
        return "ผลตรวจอยู่ในเกณฑ์ปกติ ควรดื่มน้ำให้เพียงพอ และตรวจสุขภาพประจำปีอย่างสม่ำเสมอ"

    if "พบน้ำตาล" in sugar_text:
        return "แนะนำตรวจน้ำตาลในเลือดเพื่อติดตามภาวะเบาหวาน"

    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_text:
        return "อาจมีประจำเดือนปน ควรตรวจซ้ำ หากผิดปกติให้พบแพทย์"

    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_text:
        return "อาจมีเลือดปนปัสสาวะ ควรตรวจซ้ำหรือตรวจเพิ่มเติมกับแพทย์"

    if "พบเม็ดเลือดขาว" in wbc_text:
        return "อาจมีการติดเชื้อทางเดินปัสสาวะ ดื่มน้ำมาก ๆ และไม่ควรกลั้นปัสสาวะ"

    if urine_result == "ผลปัสสาวะผิดปกติ":
        return "ควรตรวจปัสสาวะซ้ำ หากมีอาการควรพบแพทย์"

    return ""

# === แปลผล ===
alb_text = translate_alb(alb_raw)
sugar_text = translate_sugar(sugar_raw)
rbc_text = translate_rbc(rbc_raw)
wbc_text = translate_wbc(wbc_raw)

# === แสดงผล ===
if urine_result or alb_raw or sugar_raw or rbc_raw or wbc_raw:
    st.markdown(f"### 💧 ผลการตรวจปัสสาวะ ปี พ.ศ. 25{selected_year}")
    st.markdown(f"- **สรุปผลรวม:** {urine_result if urine_result else '-'}")

    st.markdown("#### รายละเอียด")
    st.markdown(f"""
    - **โปรตีนในปัสสาวะ:** {alb_raw or '-'} ({alb_text})
    - **น้ำตาลในปัสสาวะ:** {sugar_raw or '-'} ({sugar_text})
    - **เม็ดเลือดแดง:** {rbc_raw or '-'} ({rbc_text})
    - **เม็ดเลือดขาว:** {wbc_raw or '-'} ({wbc_text})
    """)

    urine_advice = urine_advice_interpret(
        sex=person.get("เพศ", ""),
        alb_text=alb_text,
        sugar_text=sugar_text,
        rbc_text=rbc_text,
        wbc_text=wbc_text,
        urine_result=urine_result
    )

    if urine_advice:
        st.warning(f"📌 คำแนะนำ: {urine_advice}")
