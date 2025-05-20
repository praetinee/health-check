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
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str)
df['HN'] = df['HN'].astype(str)
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str)

# ===============================
# SEARCH UI
# ===============================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    citizen_id = st.text_input("เลขบัตรประชาชน", max_chars=13, placeholder="เช่น 1234567890123")
with col2:
    hn = st.text_input("HN", placeholder="เช่น 123456")
with col3:
    full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี")

if st.button("ตรวจสอบ"):
    if not (citizen_id.strip() or hn.strip() or full_name.strip()):
        st.warning("⚠️ กรุณากรอกอย่างน้อยหนึ่งช่องเพื่อค้นหา")
    else:
        matched = df[
            (df['เลขบัตรประชาชน'] == citizen_id.strip()) |
            (df['HN'] == hn.strip()) |
            (df['ชื่อ-สกุล'].str.strip() == full_name.strip())
        ]

        if matched.empty:
            st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        else:
            person = matched.iloc[0]
            st.success(f"✅ พบข้อมูลของ {person.get('ชื่อ-สกุล', '-')}")
            st.markdown(f"**HN:** {person.get('HN', '-')}  ")
            st.markdown(f"**เลขบัตรประชาชน:** {person.get('เลขบัตรประชาชน', '-')}")
            st.markdown(f"**เพศ:** {person.get('เพศ', '-')}")

            # ===============================
            # HEALTH SECTION - SELECT YEAR
            # ===============================
            st.markdown("### 🗓️ เลือกปี พ.ศ. ที่ต้องการดูผลสุขภาพ")
            selected_year_display = st.selectbox("เลือกปี", [f"พ.ศ. 25{y}" for y in range(61, 69)])
            selected_year = selected_year_display[-2:]

            def calc_bmi(w, h):
                try:
                    return round(float(w) / ((float(h)/100)**2), 1)
                except:
                    return None

            def interpret_bmi(bmi):
                if bmi is None: return None
                if bmi > 30: return "อ้วนมาก"
                elif bmi >= 25: return "อ้วน"
                elif bmi >= 23: return "น้ำหนักเกิน"
                elif bmi >= 18.5: return "ปกติ"
                else: return "ผอม"

            def interpret_bp(sbp, dbp):
                try:
                    sbp = float(sbp)
                    dbp = float(dbp)
                    if sbp == 0 or dbp == 0: return None
                    if sbp >= 160 or dbp >= 100: return "ความดันโลหิตสูง"
                    elif sbp >= 140 or dbp >= 90: return "ความดันโลหิตสูงเล็กน้อย"
                    elif sbp < 120 and dbp < 80: return "ความดันโลหิตปกติ"
                    else: return "ความดันโลหิตปกติค่อนข้างสูง"
                except:
                    return None

            def assess_waist(waist):
                try:
                    return "รอบเอวเกินเกณฑ์" if float(waist) > 90 else "รอบเอวปกติ"
                except:
                    return None

            def get_value(field):
                return person.get(f"{field}{selected_year}", "-")

            weight = get_value("น้ำหนัก")
            height = get_value("ส่วนสูง")
            waist = get_value("รอบเอว")
            sbp = get_value("SBP")
            dbp = get_value("DBP")
            pulse = get_value("pulse")

            bmi = calc_bmi(weight, height)
            bmi_text = f"{bmi:.1f}" if bmi else "-"
            bmi_result = interpret_bmi(bmi)
            bp_text = f"{sbp}/{dbp}" if sbp != "-" and dbp != "-" else "-"
            bp_result = interpret_bp(sbp, dbp)
            waist_result = assess_waist(waist)

            st.markdown("### 🡉 ข้อมูลทั่วไป (เฉพาะปีที่เลือก)")
            data_summary = pd.DataFrame({
                "น้ำหนัก (กก.)": [weight],
                "ส่วนสูง (ซม.)": [height],
                "รอบเอว (ซม.)": [waist],
                "BMI": [bmi_text],
                "แปลผล BMI": [bmi_result or "-"],
                "ค่าความดัน (mmHg)": [bp_text],
                "แปลผลความดัน": [bp_result or "-"],
                "แปลผลรอบเอว": [waist_result or "-"],
                "ชีพจร (bpm)": [pulse]
            })
            st.dataframe(data_summary.T.rename(columns={0: selected_year_display}), use_container_width=True)
