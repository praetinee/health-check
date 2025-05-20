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

# เปลี่ยน URL ตามไฟล์ใหม่ที่คุณใช้
sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
spreadsheet = client.open_by_url(sheet_url)
worksheet = spreadsheet.sheet1
df = pd.DataFrame(worksheet.get_all_records())

# ล้างช่องว่างในชื่อคอลัมน์เพื่อให้ตรงกับชื่อจริง
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str)
df['HN'] = df['HN'].astype(str)
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str)

# ===============================
# SEARCH UI
# ===============================
st.markdown("<h1 style='text-align:center;'>🔍 ตรวจสอบผลสุขภาพของคุณ</h1>", unsafe_allow_html=True)

# ช่องกรอกข้อมูลแนวนอน
col1, col2, col3 = st.columns(3)
with col1:
    id_card = st.text_input("เลขบัตรประชาชน", placeholder="เช่น 1234567890123")
with col2:
    hn = st.text_input("HN", placeholder="เช่น 012345")
with col3:
    full_name = st.text_input("ชื่อ-สกุล", placeholder="เช่น สมชาย ใจดี")

# ปุ่มค้นหา (อยู่นอก columns)
if st.button("ค้นหา"):
    result = pd.DataFrame()

    if id_card.strip():
        result = df[df["เลขบัตรประชาชน"] == id_card.strip()]
    elif hn.strip():
        result = df[df["HN"] == hn.strip()]
    elif full_name.strip():
        result = df[df["ชื่อ-สกุล"] == full_name.strip()]

    if result.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.write("🔎 ลองตรวจสอบชื่อคอลัมน์ใน Google Sheets และชื่อ-นามสกุล หรือ HN อีกครั้ง")
    else:
        person = result.iloc[0]
        st.success(f"✅ พบข้อมูลของ {person.get('ชื่อ-สกุล', '-')}")
        st.markdown(f"""
        **HN:** {person.get('HN', '-')}  
        **เลขบัตรประชาชน:** {person.get('เลขบัตรประชาชน', '-')}  
        **เพศ:** {person.get('เพศ', '-')}  
        """)
        st.dataframe(person.to_frame().T, use_container_width=True)

# ===============================
# HEALTH FUNCTIONS
# ===============================
def calc_bmi(w, h):
    try:
        h = float(h)
        w = float(w)
        return round(w / ((h / 100) ** 2), 1)
    except:
        return None

def interpret_bmi(bmi):
    if not bmi: return None
    if bmi > 30: return "อ้วนมาก"
    elif bmi >= 25: return "อ้วน"
    elif bmi >= 23: return "น้ำหนักเกิน"
    elif bmi >= 18.5: return "ปกติ"
    else: return "ผอม"

def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return None
        if sbp >= 160 or dbp >= 100: return "ความดันโลหิตสูง"
        elif sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80: return "ความดันปกติ"
        else: return "ความดันปกติค่อนข้างสูง"
    except:
        return None

def assess_waist(waist, threshold=90):
    try:
        waist = float(waist)
        if waist == 0: return None
        return "รอบเอวเกินเกณฑ์" if waist > threshold else "รอบเอวปกติ"
    except:
        return None

def combined_interpret(bmi_result, waist_result, bp_result):
    parts = []
    if bmi_result:
        parts.append(f"{bmi_result}")
    if waist_result:
        parts.append(waist_result)
    if bp_result:
        parts.append(bp_result)
    return " / ".join(parts) if parts else "-"

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
        # ค้นหาด้วยเงื่อนไขใดเงื่อนไขหนึ่ง
        matched = df[
            (df["เลขบัตรประชาชน"] == citizen_id.strip()) |
            (df["HN"].astype(str) == hn.strip()) |
            (df["ชื่อ-สกุล"].str.contains(full_name.strip(), case=False, na=False))
        ]

        if matched.empty:
            st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        else:
            person = matched.iloc[0]

        if matched.empty:
            st.error("ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        else:
            person = matched.iloc[0]
            st.success(f"✅ พบข้อมูล: {person.get('ชื่อ-สกุล', '-')}")
            st.markdown(f"**เพศ:** {person.get('เพศ', '-')}")

            # ปีที่จะแสดงผล
            years = list(range(61, 69))  # พ.ศ. 2561 - 2568
            display_years = [f"พ.ศ. 25{y}" for y in years]

            def get_values(prefix):
                return [person.get(f"{prefix}{y}", "-") for y in years]

            weights = get_values("น้ำหนัก")
            heights = get_values("ส่วนสูง")
            waists = get_values("รอบเอว")
            sbps = get_values("SBP")
            dbps = get_values("DBP")

            bmi_results = []
            bp_values = []
            interpretations = []

            for w, h, sbp, dbp, waist in zip(weights, heights, sbps, dbps, waists):
                bmi = calc_bmi(w, h)
                bmi_result = interpret_bmi(bmi)
                waist_result = assess_waist(waist)
                bp_result = interpret_bp(sbp, dbp)

                bmi_results.append(f"{bmi:.1f}" if bmi else "-")
                bp_values.append(f"{sbp}/{dbp}" if sbp != "-" and dbp != "-" else "-")
                interpretations.append(combined_interpret(bmi_result, waist_result, bp_result))

            summary_df = pd.DataFrame({
                "ปี พ.ศ.": display_years,
                "น้ำหนัก (กก.)": weights,
                "ส่วนสูง (ซม.)": heights,
                "รอบเอว (ซม.)": waists,
                "ค่าความดัน (mmHg)": bp_values,
                "แปลผล": interpretations
            })

            st.markdown("### 🩺 น้ำหนัก/รอบเอว/ความดัน")
            st.dataframe(summary_df.set_index("ปี พ.ศ.").T, use_container_width=True)

            # ===============================
            # แสดงผลปัสสาวะ
            # ===============================
            st.markdown("### 🚻 ผลตรวจปัสสาวะ")

            alb = person.get("Alb68", "").strip()
            sugar = person.get("sugar68", "").strip()
            rbc = person.get("RBC168", "").strip()
            wbc = person.get("WBC168", "").strip()

            if alb == "":
                alb_result = ""
            elif alb.lower() == "negative":
                alb_result = "ไม่พบโปรตีนในปัสสาวะ"
            elif alb in ["trace", "1+", "2+"]:
                alb_result = "พบโปรตีนในปัสสาวะเล็กน้อย"
            elif alb == "3+":
                alb_result = "พบโปรตีนในปัสสาวะ"
            else:
                alb_result = alb

            if sugar == "":
                sugar_result = ""
            elif sugar.lower() == "negative":
                sugar_result = "ไม่พบน้ำตาลในปัสสาวะ"
            elif sugar == "trace":
                sugar_result = "พบน้ำตาลในปัสสาวะเล็กน้อย"
            elif sugar in ["1+", "2+", "3+", "4+", "5+", "6+"]:
                sugar_result = "พบน้ำตาลในปัสสาวะ"
            else:
                sugar_result = sugar

            if rbc == "":
                rbc_result = ""
            elif rbc.lower() in ["negative", "0-1", "1-2", "2-3", "3-5"]:
                rbc_result = "ปกติ"
            elif rbc in ["5-10", "10-20"]:
                rbc_result = "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
            else:
                rbc_result = "พบเม็ดเลือดแดงในปัสสาวะ"

            if wbc == "":
                wbc_result = ""
            elif wbc.lower() in ["negative", "0-1", "1-2", "2-3", "3-5"]:
                wbc_result = "ปกติ"
            elif wbc in ["5-10", "10-20"]:
                wbc_result = "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
            else:
                wbc_result = "พบเม็ดเลือดขาวในปัสสาวะ"

            # ✅ แก้ตรงนี้ให้ตรวจค่าแบบตรง
            abnormal_flags = [
                alb_result not in ["", "ไม่พบโปรตีนในปัสสาวะ", "พบโปรตีนในปัสสาวะเล็กน้อย"],
                sugar_result not in ["", "ไม่พบน้ำตาลในปัสสาวะ", "พบน้ำตาลในปัสสาวะเล็กน้อย"],
                rbc_result not in ["", "ปกติ", "เม็ดเลือดแดงในปัสสาวะปกติ"],
                wbc_result not in ["", "ปกติ", "เม็ดเลือดขาวในปัสสาวะปกติ"]
            ]

            if all(v == "" for v in [alb_result, sugar_result, rbc_result, wbc_result]):
                overall_result = "-"
            elif any(abnormal_flags):
                overall_result = "ผลปัสสาวะผิดปกติ"
            else:
                overall_result = "ปัสสาวะปกติ"

            st.markdown(f"""
            <table style='width:100%; font-size:20px; border-collapse: collapse;' border=1>
            <tr><th>รายการ</th><th>ผล</th></tr>
            <tr><td>โปรตีนในปัสสาวะ</td><td>{alb_result or '-'}</td></tr>
            <tr><td>น้ำตาลในปัสสาวะ</td><td>{sugar_result or '-'}</td></tr>
            <tr><td>เม็ดเลือดแดง</td><td>{rbc_result or '-'}</td></tr>
            <tr><td>เม็ดเลือดขาว</td><td>{wbc_result or '-'}</td></tr>
            <tr><td><b>สรุปผล</b></td><td><b>{overall_result}</b></td></tr>
            </table>
            """, unsafe_allow_html=True)
