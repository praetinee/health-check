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
# CONNECT GOOGLE SHEET (ปลอดภัยแม้เปลี่ยน sheet แรก)
# ===============================
try:
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)

    sheet_url = "https://docs.google.com/spreadsheets/d/1N3l0o_Y6QYbGKx22323mNLPym77N0jkJfyxXFM2BDmc"
    worksheet = client.open_by_url(sheet_url).sheet1  # ✅ sheet แรกเสมอ

    raw_data = worksheet.get_all_records()  # ✅ พยายามอ่านข้อมูล
    if not raw_data:
        st.error("❌ ไม่พบข้อมูลในแผ่นแรกของ Google Sheet")
        st.stop()

    df = pd.DataFrame(raw_data)

    # ✅ ทำความสะอาดชื่อคอลัมน์และข้อมูลสำคัญ
    df.columns = df.columns.str.strip()
    df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
    df['HN'] = df['HN'].astype(str).str.strip()
    df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลด Google Sheet: {e}")
    st.stop()
    
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
            return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90:
            return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80:
            return "ความดันปกติ"
        else:
            return "ความดันค่อนข้างสูง"
    except:
        return "-"

# 🩸 ข้อความคำแนะนำ CBC แบบกระชับ
cbc_messages = {
    2:  "ดูแลสุขภาพ ออกกำลังกาย ทานอาหารมีประโยชน์ ติดตามผลเลือดสม่ำเสมอ",
    4:  "ควรพบแพทย์เพื่อตรวจหาสาเหตุเกล็ดเลือดต่ำ และเฝ้าระวังอาการผิดปกติ",
    6:  "ควรตรวจซ้ำเพื่อติดตามเม็ดเลือดขาว และดูแลสุขภาพร่างกายให้แข็งแรง",
    8:  "ควรพบแพทย์เพื่อตรวจหาสาเหตุภาวะโลหิตจาง และรักษาตามนัด",
    9:  "ควรพบแพทย์เพื่อตรวจหาและติดตามภาวะโลหิตจางร่วมกับเม็ดเลือดขาวผิดปกติ",
    10: "ควรพบแพทย์เพื่อตรวจหาสาเหตุเกล็ดเลือดสูง และพิจารณาการรักษา",
    13: "ควรดูแลสุขภาพ ติดตามภาวะโลหิตจางและเม็ดเลือดขาวผิดปกติอย่างใกล้ชิด",
}

# 🩸 ฟังก์ชันให้คำแนะนำ CBC (ตามสูตร Excel)
def cbc_advice(hb_result, wbc_result, plt_result):
    if all(x in ["", "-", None] for x in [hb_result, wbc_result, plt_result]):
        return "-"

    hb = hb_result.strip()
    wbc = wbc_result.strip()
    plt = plt_result.strip()

    # ✅ Plt ต่ำต้องตรวจสอบก่อน เพราะสูตร Excel ให้ความสำคัญเป็นพิเศษ
    if plt in ["ต่ำกว่าเกณฑ์", "ต่ำกว่าเกณฑ์เล็กน้อย"]:
        return cbc_messages[4]

    if hb == "ปกติ" and wbc == "ปกติ" and plt == "ปกติ":
        return ""

    if hb == "พบภาวะโลหิตจาง" and wbc == "ปกติ" and plt == "ปกติ":
        return cbc_messages[8]

    if hb == "พบภาวะโลหิตจาง" and wbc in [
        "ต่ำกว่าเกณฑ์", 
        "ต่ำกว่าเกณฑ์เล็กน้อย", 
        "สูงกว่าเกณฑ์เล็กน้อย", 
        "สูงกว่าเกณฑ์"
    ]:
        return cbc_messages[9]

    if hb == "พบภาวะโลหิตจางเล็กน้อย" and wbc == "ปกติ" and plt == "ปกติ":
        return cbc_messages[2]

    if hb == "ปกติ" and wbc in [
        "ต่ำกว่าเกณฑ์", 
        "ต่ำกว่าเกณฑ์เล็กน้อย", 
        "สูงกว่าเกณฑ์เล็กน้อย", 
        "สูงกว่าเกณฑ์"
    ]:
        return cbc_messages[6]

    if plt == "สูงกว่าเกณฑ์":
        return cbc_messages[10]

    if hb == "พบภาวะโลหิตจางเล็กน้อย" and \
       wbc in [
           "ต่ำกว่าเกณฑ์", 
           "ต่ำกว่าเกณฑ์เล็กน้อย", 
           "สูงกว่าเกณฑ์เล็กน้อย", 
           "สูงกว่าเกณฑ์"
       ] and plt == "ปกติ":
        return cbc_messages[13]

    return "ควรพบแพทย์เพื่อตรวจเพิ่มเติม"

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
    submitted = st.form_submit_button("ค้นหา")  # ✅ สร้างตัวแปรตรงนี้เท่านั้น!

# ✅ หลังจาก form เสร็จแล้ว ถึงใช้ได้
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
        if "person" in st.session_state:
            del st.session_state["person"]  # 👈 ล้างข้อมูลเก่าทันที

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
        cols = columns_by_year[y]  # ✅ ต้องอยู่ในลูปเท่านั้น!

        weight = person.get(cols["weight"], "")
        height = person.get(cols["height"], "")

        try:
            weight = float(weight)
            height = float(height)
            if weight > 0 and height > 0:
                bmi_val = round(weight / ((height / 100) ** 2), 1)
                bmi_data.append(bmi_val)
                labels.append(f"B.E. {y + 2500}")
        except:
            continue

    if bmi_data and labels:
        st.markdown("### 📈 BMI Trend")
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.axhspan(30, 40, facecolor='#D32F2F', alpha=0.3, label='Severely Obese')
        ax.axhspan(25, 30, facecolor='#FF5722', alpha=0.3, label='Obese')
        ax.axhspan(23, 25, facecolor='#FF9900', alpha=0.3, label='Overweight')
        ax.axhspan(18.5, 23, facecolor='#109618', alpha=0.3, label='Normal')
        ax.axhspan(0, 18.5, facecolor='#3366CC', alpha=0.3, label='Underweight')

        ax.plot(np.arange(len(labels)), bmi_data, marker='o', color='black', linewidth=2, label='BMI')
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel("BMI", fontsize=12)
        ax.set_ylim(15, 40)
        ax.set_title("BMI Over Time", fontsize=14)
        ax.legend(loc="upper left")

        st.pyplot(fig)
    else:
        st.info("ไม่มีข้อมูล BMI เพียงพอสำหรับแสดงกราฟ")

    # ===============================
    # DISPLAY: URINE TEST (ปี 2561–2568)
    # ===============================
    
    def interpret_alb(value):
        if value == "":
            return "-"
        if value.lower() == "negative":
            return "ไม่พบ"
        elif value in ["trace", "1+", "2+"]:
            return "พบโปรตีนในปัสสาวะเล็กน้อย"
        elif value == "3+":
            return "พบโปรตีนในปัสสาวะ"
        return "-"
    
    def interpret_sugar(value):
        if value == "":
            return "-"
        if value.lower() == "negative":
            return "ไม่พบ"
        elif value == "trace":
            return "พบน้ำตาลในปัสสาวะเล็กน้อย"
        elif value in ["1+", "2+", "3+", "4+", "5+", "6+"]:
            return "พบน้ำตาลในปัสสาวะ"
        return "-"
    
    def interpret_rbc(value):
        if value == "":
            return "-"
        if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
            return "ปกติ"
        elif value in ["5-10", "10-20"]:
            return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
        else:
            return "พบเม็ดเลือดแดงในปัสสาวะ"
    
    def interpret_wbc(value):
        if value == "":
            return "-"
        if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
            return "ปกติ"
        elif value in ["5-10", "10-20"]:
            return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
        else:
            return "พบเม็ดเลือดขาวในปัสสาวะ"
    
    def summarize_urine(*results):
        if all(
            r in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"]
            for r in results
        ):
            return "ปกติ"
        if any("พบ" in r and "เล็กน้อย" not in r for r in results):
            return "ผิดปกติ"
        if any("เม็ดเลือดแดง" in r or "เม็ดเลือดขาว" in r for r in results if "ปกติ" not in r):
            return "ผิดปกติ"
        return "-"
    
    def advice_urine(sex, alb, sugar, rbc, wbc):
        alb_text = interpret_alb(alb)
        sugar_text = interpret_sugar(sugar)
        rbc_text = interpret_rbc(rbc)
        wbc_text = interpret_wbc(wbc)
    
        if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"]
               for x in [alb_text, sugar_text, rbc_text, wbc_text]):
            return "ผลปัสสาวะอยู่ในเกณฑ์ปกติ ควรรักษาสุขภาพและตรวจประจำปีสม่ำเสมอ"
    
        if "พบน้ำตาลในปัสสาวะ" in sugar_text and "เล็กน้อย" not in sugar_text:
            return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    
        if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_text and "ปกติ" in wbc_text:
            return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    
        if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_text and "ปกติ" in wbc_text:
            return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    
        if "พบเม็ดเลือดขาวในปัสสาวะ" in wbc_text and "เล็กน้อย" not in wbc_text:
            return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
    
        return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"
    
    # ===============================
    # เตรียมตาราง
    # ===============================
    sex = person.get("เพศ", "")
    advice_latest = "-"
    urine_table = {
        "โปรตีน": [],
        "น้ำตาล": [],
        "เม็ดเลือดแดง": [],
        "เม็ดเลือดขาว": [],
        "ผลสรุป": []
    }
    
    for y in years:
        y_label = str(y) if y != 68 else ""
        y_be = y + 2500
    
        alb_col = f"Alb{y_label}"
        sugar_col = f"sugar{y_label}"
        rbc_col = f"RBC1{y_label}"
        wbc_col = f"WBC1{y_label}"
        summary_col = f"ผลปัสสาวะ{y_label}" if y != 68 else None
    
        alb_raw = person.get(alb_col, "").strip()
        sugar_raw = person.get(sugar_col, "").strip()
        rbc_raw = person.get(rbc_col, "").strip()
        wbc_raw = person.get(wbc_col, "").strip()
    
        alb = f"{alb_raw}<br><span style='font-size:13px;color:gray;'>{interpret_alb(alb_raw)}</span>" if alb_raw else "-"
        sugar = f"{sugar_raw}<br><span style='font-size:13px;color:gray;'>{interpret_sugar(sugar_raw)}</span>" if sugar_raw else "-"
        rbc = f"{rbc_raw}<br><span style='font-size:13px;color:gray;'>{interpret_rbc(rbc_raw)}</span>" if rbc_raw else "-"
        wbc = f"{wbc_raw}<br><span style='font-size:13px;color:gray;'>{interpret_wbc(wbc_raw)}</span>" if wbc_raw else "-"
    
        if y >= 68:
            if not any([alb_raw, sugar_raw, rbc_raw, wbc_raw]):
                summary = "-"
            else:
                summary = summarize_urine(
                    interpret_alb(alb_raw),
                    interpret_sugar(sugar_raw),
                    interpret_rbc(rbc_raw),
                    interpret_wbc(wbc_raw)
                )
            
            # สร้าง advice เฉพาะปี 68 เท่านั้น (หรือปรับ y == ปีอื่นก็ได้)
            if y == 68:
                advice_latest = (
                    advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
                    if any([alb_raw, sugar_raw, rbc_raw, wbc_raw])
                    else "-"
                )

        else:
            summary = person.get(summary_col, "").strip() or "-"
            summary = "ผิดปกติ" if "ผิดปกติ" in summary else ("ปกติ" if "ปกติ" in summary else "-")

        urine_table["โปรตีน"].append(alb)
        urine_table["น้ำตาล"].append(sugar)
        urine_table["เม็ดเลือดแดง"].append(rbc)
        urine_table["เม็ดเลือดขาว"].append(wbc)
        urine_table["ผลสรุป"].append(summary)
    
    # ===============================
    # แสดงผลตาราง
    # ===============================
    st.markdown("### 🚽 ผลตรวจปัสสาวะ")
    urine_df = pd.DataFrame.from_dict(urine_table, orient="index", columns=[y + 2500 for y in years])
    st.markdown(urine_df.to_html(escape=False), unsafe_allow_html=True)
    
    # ===============================
    # แสดงคำแนะนำปี 68 หรือมากกว่า
    # ===============================
    latest_year = None
    for y in reversed(years):
        if y >= 68:
            y_label = str(y)
            if any(person.get(f"{prefix}{y_label}", "").strip() for prefix in ["Alb", "sugar", "RBC1", "WBC1"]):
                latest_year = y
                break
    
    # อย่าเขียนทับ advice_latest ถ้ามีค่าที่ไม่ใช่ "-"
    if advice_latest == "-":
        if latest_year is not None:
            y_label = str(latest_year)
            alb_raw = person.get(f"Alb{y_label}", "").strip()
            sugar_raw = person.get(f"sugar{y_label}", "").strip()
            rbc_raw = person.get(f"RBC1{y_label}", "").strip()
            wbc_raw = person.get(f"WBC1{y_label}", "").strip()
            advice_latest = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
    
    # แสดงคำแนะนำเฉพาะถ้าไม่ใช่ "ปกติ" และไม่ใช่ "-"
    if advice_latest and advice_latest not in ["-", ""] and "ปกติ" not in advice_latest:
        st.markdown(f"""
        <div style='
            background-color: rgba(255, 215, 0, 0.2);
            padding: 1rem;
            border-radius: 6px;
            color: white;
        '>
            <div style='font-size: 18px; font-weight: bold;'>📌 คำแนะนำผลตรวจปัสสาวะปี 2568</div>
            <div style='font-size: 16px; margin-top: 0.3rem;'>{advice_latest}</div>
        </div>
        """, unsafe_allow_html=True)

    # ===============================
    # DISPLAY: STOOL TEST
    # ===============================
    
    def interpret_stool_exam(value):
        if not value or value.strip() == "":
            return "-"
        if "ปกติ" in value:
            return "ปกติ"
        elif "เม็ดเลือดแดง" in value:
            return "พบเม็ดเลือดแดงในอุจจาระ นัดตรวจซ้ำ"
        elif "เม็ดเลือดขาว" in value:
            return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
        return value.strip()
    
    def interpret_stool_cs(value, is_latest=False):
        if not value or value.strip() == "":
            return "-"
        if "ไม่พบ" in value or "ปกติ" in value:
            return "ไม่พบการติดเชื้อ"
        if is_latest:
            return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"
        return "พบการติดเชื้อในอุจจาระ"
    
    st.markdown("### 💩 ผลตรวจอุจจาระ")
    
    stool_table = {
        "ผลตรวจอุจจาระทั่วไป": [],
        "ผลเพาะเชื้ออุจจาระ": []
    }
    
    latest_year = max(years)
    
    for y in years:
        y_label = "" if y == 68 else str(y)
        year_be = y + 2500
    
        exam_col = f"Stool exam{y_label}"
        cs_col = f"Stool C/S{y_label}"
    
        exam_raw = person.get(exam_col, "").strip()
        cs_raw = person.get(cs_col, "").strip()
    
        is_latest = y == latest_year
    
        exam_text = interpret_stool_exam(exam_raw)
        cs_text = interpret_stool_cs(cs_raw, is_latest=is_latest)
    
        stool_table["ผลตรวจอุจจาระทั่วไป"].append(exam_text)
        stool_table["ผลเพาะเชื้ออุจจาระ"].append(cs_text)
    
    # แสดงเป็น DataFrame
    stool_df = pd.DataFrame.from_dict(stool_table, orient="index", columns=[y + 2500 for y in years])
    st.markdown(stool_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: BLOOD TEST (CBC)
    # ===============================
    
    def interpret_wbc(wbc):
        try:
            wbc = float(wbc)
            if wbc == 0:
                return "-"
            elif 4000 <= wbc <= 10000:
                return "ปกติ"
            elif 10000 < wbc < 13000:
                return "สูงกว่าเกณฑ์เล็กน้อย"
            elif wbc >= 13000:
                return "สูงกว่าเกณฑ์ปกติ"
            elif 3000 < wbc < 4000:
                return "ต่ำกว่าเกณฑ์เล็กน้อย"
            elif wbc <= 3000:
                return "ต่ำกว่าเกณฑ์ปกติ"
        except:
            return "-"
        return "-"
    
    def interpret_hb(hb, sex):
        try:
            hb = float(hb)
            if sex == "ชาย":
                if hb < 12:
                    return "พบภาวะโลหิตจาง"
                elif 12 <= hb < 13:
                    return "พบภาวะโลหิตจางเล็กน้อย"
                else:
                    return "ปกติ"
            elif sex == "หญิง":
                if hb < 11:
                    return "พบภาวะโลหิตจาง"
                elif 11 <= hb < 12:
                    return "พบภาวะโลหิตจางเล็กน้อย"
                else:
                    return "ปกติ"
        except:
            return "-"
        return "-"
    
    def interpret_plt(plt):
        try:
            plt = float(plt)
            if plt == 0:
                return "-"
            elif 150000 <= plt <= 500000:
                return "ปกติ"
            elif 500000 < plt < 600000:
                return "สูงกว่าเกณฑ์เล็กน้อย"
            elif plt >= 600000:
                return "สูงกว่าเกณฑ์"
            elif 100000 <= plt < 150000:
                return "ต่ำกว่าเกณฑ์เล็กน้อย"
            elif plt < 100000:
                return "ต่ำกว่าเกณฑ์"
        except:
            return "-"
        return "-"
    
    st.markdown("### 🩸 ความสมบูรณ์ของเลือด")
    
    blood_table = {
        "เม็ดเลือดขาว (WBC)": [],
        "ความเข้มข้นของเลือด (Hb%)": [],
        "เกล็ดเลือด (Plt)": []
    }
    
    sex = person.get("เพศ", "").strip()
    
    for y in years:
        y_label = "" if y == 68 else str(y)
        year_be = y + 2500
    
        wbc_raw = str(person.get(f"WBC (cumm){y_label}", "")).strip()
        hb_raw = str(person.get(f"Hb(%){y_label}", "")).strip()
        plt_raw = str(person.get(f"Plt (/mm){y_label}", "")).strip()
    
        blood_table["เม็ดเลือดขาว (WBC)"].append(interpret_wbc(wbc_raw))
        blood_table["ความเข้มข้นของเลือด (Hb%)"].append(interpret_hb(hb_raw, sex))
        blood_table["เกล็ดเลือด (Plt)"].append(interpret_plt(plt_raw))
    
    blood_df = pd.DataFrame.from_dict(blood_table, orient="index", columns=[y + 2500 for y in years])
    st.markdown(blood_df.to_html(escape=False), unsafe_allow_html=True)

    # คำนวณคำแนะนำ CBC ปีล่าสุด (2568)
    latest_y = 68
    y_label = ""  # สำหรับปี 68 คอลัมน์ไม่มี suffix
    
    wbc_raw = str(person.get(f"WBC (cumm){y_label}", "")).strip()
    hb_raw = str(person.get(f"Hb(%){y_label}", "")).strip()
    plt_raw = str(person.get(f"Plt (/mm){y_label}", "")).strip()
    
    wbc_result = interpret_wbc(wbc_raw)
    hb_result = interpret_hb(hb_raw, sex)
    plt_result = interpret_plt(plt_raw)
    
    cbc_recommendation = cbc_advice(hb_result, wbc_result, plt_result)
    
    # แสดงคำแนะนำ เฉพาะเมื่อมีข้อมูลอย่างน้อย 1 ค่าที่ไม่ใช่ "-"
    if cbc_recommendation and not all(x == "-" for x in [wbc_result, hb_result, plt_result]):
        st.markdown(f"""
        <div style='
            background-color: rgba(255, 105, 135, 0.15);
            padding: 1rem;
            border-radius: 6px;
            color: white;
        '>
            <div style='font-size: 18px; font-weight: bold;'>📌 คำแนะนำผลตรวจเลือด (CBC) ปี 2568</div>
            <div style='font-size: 16px; margin-top: 0.3rem;'>{cbc_recommendation}</div>
        </div>
        """, unsafe_allow_html=True)

    # ===============================
    # DISPLAY: LIVER TEST (การทำงานของตับ)
    # ===============================
    
    import pandas as pd
    import streamlit as st
    
    years = list(range(2561, 2569))
    
    alp_raw = str(person.get(f"ALP{y_label}", "") or "").strip()
    sgot_raw = str(person.get(f"SGOT{y_label}", "") or "").strip()
    sgpt_raw = str(person.get(f"SGPT{y_label}", "") or "").strip()

    st.markdown("### 🧪 การทำงานของตับ")
    
    def interpret_liver(value, upper_limit):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif value > upper_limit:
                return f"{value}<br><span style='font-size:13px;color:gray;'>สูงกว่าเกณฑ์</span>", "สูง"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>", "ปกติ"
        except:
            return "-", "-"
    
    def summarize_liver(alp_val, sgot_val, sgpt_val):
        try:
            alp = float(alp_val)
            sgot = float(sgot_val)
            sgpt = float(sgpt_val)
            if alp == 0 or sgot == 0 or sgpt == 0:
                return "-"
            if alp > 120 or sgot > 36 or sgpt > 40:
                return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
            return "ปกติ"
        except:
            return "-"
    
    def liver_advice(summary_text):
        if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
            return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
        elif summary_text == "ปกติ":
            return ""
        return "-"
    
    # เตรียมตาราง
    liver_data = {
        "ระดับเอนไซม์ ALP": [],
        "SGOT (AST)": [],
        "SGPT (ALT)": [],
        "ผลสรุป": []
    }
    
    advice_liver = "-"
    
    for y in years:
        y_label = "" if y == 2568 else str(y % 100)
        year_be = y
    
        alp_raw = str(person.get(f"ALP{y_label}", "") or "").strip()
        sgot_raw = str(person.get(f"SGOT{y_label}", "") or "").strip()
        sgpt_raw = str(person.get(f"SGPT{y_label}", "") or "").strip()
    
        alp_disp, alp_flag = interpret_liver(alp_raw, 120)
        sgot_disp, sgot_flag = interpret_liver(sgot_raw, 36)
        sgpt_disp, sgpt_flag = interpret_liver(sgpt_raw, 40)
    
        summary = summarize_liver(alp_raw, sgot_raw, sgpt_raw)
    
        liver_data["ระดับเอนไซม์ ALP"].append(alp_disp)
        liver_data["SGOT (AST)"].append(sgot_disp)
        liver_data["SGPT (ALT)"].append(sgpt_disp)
        liver_data["ผลสรุป"].append(summary)
    
        # เก็บคำแนะนำเฉพาะปีล่าสุด
        if y == 2568:
            advice_liver = liver_advice(summary)
    
    # แสดงตาราง
    liver_df = pd.DataFrame.from_dict(liver_data, orient="index", columns=[y for y in years])
    st.markdown(liver_df.to_html(escape=False), unsafe_allow_html=True)
    
    # แสดงเฉพาะเมื่อมีความผิดปกติ
    if advice_liver and advice_liver != "-" and advice_liver != "":
        st.markdown(f"""
        <div style='
            background-color: rgba(100, 221, 23, 0.15);
            padding: 1rem;
            border-radius: 6px;
            color: white;
        '>
            <div style='font-size: 18px; font-weight: bold;'>📌 คำแนะนำผลตรวจตับ ปี 2568</div>
            <div style='font-size: 16px; margin-top: 0.3rem;'>{advice_liver}</div>
        </div>
        """, unsafe_allow_html=True)

    # ===============================
    # DISPLAY: URIC ACID (ผลยูริคในเลือด)
    # ===============================
    st.markdown("### 🧪 ผลกรดยูริคในเลือด")
    
    # สร้างชื่อคอลัมน์แบบยืดหยุ่นตามปี
    def get_uric_col_name(year):
        return "Uric Acid" if year == 2568 else f"Uric Acid{str(year)[-2:]}"
    
    # ฟังก์ชันแปลผลยูริค
    def interpret_uric(value):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif value > 7.2:
                return f"{value}<br><span style='font-size:13px;color:gray;'>สูงกว่าเกณฑ์</span>"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    # เตรียมตารางผล
    uric_data = []
    for y in range(2561, 2569):
        col_name = get_uric_col_name(y)
        raw_value = str(person.get(col_name, "") or "").strip()
        result = interpret_uric(raw_value)
        uric_data.append(result)
    
    # สร้าง DataFrame
    uric_df = pd.DataFrame({
        "กรดยูริคในเลือด (mg/dL)": uric_data
    }, index=[y for y in range(2561, 2569)]).T
    
    # แสดงผล
    st.markdown(uric_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: KIDNEY FUNCTION (ผลตรวจไต)
    # ===============================
    
    st.markdown("### 🧪 การทำงานของไต")
    
    # ปีที่รองรับ
    years = list(range(2561, 2569))
    
    # ฟังก์ชันแปลผลแต่ละค่า
    def interpret_bun(value):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif value < 5 or value > 20:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ผิดปกติ</span>"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    def interpret_cr(value):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif value < 0.6 or value > 1.2:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ผิดปกติ</span>"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    def interpret_gfr(value):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif value < 60:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ต่ำกว่าเกณฑ์</span>"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    # เตรียมข้อมูล
    kidney_data = {
        "BUN (mg/dL)": [],
        "Creatinine (mg/dL)": [],
        "Estimated GFR (mL/min/1.73m²)": []
    }
    
    for y in years:
        y_label = "" if y == 2568 else str(y % 100)
    
        bun_raw = str(person.get(f"BUN{y_label}", "") or "").strip()
        cr_raw = str(person.get(f"Cr{y_label}", "") or "").strip()
        gfr_raw = str(person.get(f"GFR{y_label}", "") or "").strip()
    
        kidney_data["BUN (mg/dL)"].append(interpret_bun(bun_raw))
        kidney_data["Creatinine (mg/dL)"].append(interpret_cr(cr_raw))
        kidney_data["Estimated GFR (mL/min/1.73m²)"].append(interpret_gfr(gfr_raw))
    
    # แสดงผลเป็น DataFrame
    kidney_df = pd.DataFrame.from_dict(kidney_data, orient="index", columns=[y for y in years])
    st.markdown(kidney_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: FBS (ผลตรวจน้ำตาลในเลือด)
    # ===============================
    import pandas as pd
    import streamlit as st
    
    # ===== ปีที่รองรับ =====
    years = list(range(2561, 2569))
    
    # ===== ชื่อคอลัมน์ใน Google Sheet =====
    def get_fbs_column(year):
        return "FBS" if year == 2568 else f"FBS{str(year)[-2:]}"
    
    # ===== ฟังก์ชันแปลผล FBS =====
    def interpret_fbs(value):
        try:
            value = float(value)
            if value == 0:
                return "-"
            elif 100 <= value < 106:
                return f"{value}<br><span style='font-size:13px;color:gray;'>เริ่มสูงเล็กน้อย</span>"
            elif 106 <= value < 126:
                return f"{value}<br><span style='font-size:13px;color:gray;'>สูงเล็กน้อย</span>"
            elif value >= 126:
                return f"{value}<br><span style='font-size:13px;color:gray;'>สูง</span>"
            else:
                return f"{value}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    # ===== เตรียมข้อมูลจาก person =====
    fbs_data = []
    
    for y in years:
        col_name = get_fbs_column(y)
        raw = str(person.get(col_name, "") or "").strip()
        result = interpret_fbs(raw)
        fbs_data.append(result)
    
    # ===== สร้าง DataFrame และแสดง =====
    fbs_df = pd.DataFrame({
        "ระดับน้ำตาลในเลือด (FBS) (mg/dL)": fbs_data
    }, index=years).T
    
    st.markdown("### 🍬 น้ำตาลในเลือด (FBS)")
    st.markdown(fbs_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: BLOOD LIPIDS (ไขมันในเลือด)
    # ===============================
    st.markdown("### 🧪 ไขมันในเลือด")
    
    # ปี พ.ศ. ที่รองรับ
    years = list(range(2561, 2569))  # 2561–2568
    
    # แปลผลในแต่ละรายการ
    def interpret_chol(value):
        try:
            val = float(value)
            if val == 0:
                return "-"
            elif val >= 250:
                return f"{val}<br><span style='font-size:13px;color:gray;'>สูง</span>"
            elif val <= 200:
                return f"{val}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
            else:
                return f"{val}<br><span style='font-size:13px;color:gray;'>เริ่มสูง</span>"
        except:
            return "-"
    
    def interpret_tgl(value):
        try:
            val = float(value)
            if val == 0:
                return "-"
            elif val >= 250:
                return f"{val}<br><span style='font-size:13px;color:gray;'>สูง</span>"
            elif val <= 150:
                return f"{val}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
            else:
                return f"{val}<br><span style='font-size:13px;color:gray;'>เริ่มสูง</span>"
        except:
            return "-"
    
    def interpret_hdl(value):
        try:
            val = float(value)
            if val == 0:
                return "-"
            elif val < 40:
                return f"{val}<br><span style='font-size:13px;color:gray;'>ต่ำ</span>"
            else:
                return f"{val}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    def interpret_ldl(value):
        try:
            val = float(value)
            if val == 0:
                return "-"
            elif val >= 180:
                return f"{val}<br><span style='font-size:13px;color:gray;'>สูง</span>"
            else:
                return f"{val}<br><span style='font-size:13px;color:gray;'>ปกติ</span>"
        except:
            return "-"
    
    # ฟังก์ชันสรุปไขมันในเลือดตามเกณฑ์สูตร Excel
    def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
        try:
            chol = float(chol_raw)
            tgl = float(tgl_raw)
            ldl = float(ldl_raw)
            if chol == 0 and tgl == 0:
                return "-"
            if chol >= 250 or tgl >= 250 or ldl >= 180:
                return "ไขมันในเลือดสูง"
            elif chol <= 200 and tgl <= 150:
                return "ปกติ"
            else:
                return "ไขมันในเลือดสูงเล็กน้อย"
        except:
            return "-"
    
    # เตรียมตาราง
    lipid_data = {
        "CHOL": [],
        "TGL": [],
        "HDL": [],
        "LDL": [],
        "ผลสรุป": []
    }
    
    for y in years:
        y_label = "" if y == 2568 else str(y % 100)
    
        chol_raw = str(person.get(f"CHOL{y_label}", "") or "").strip()
        tgl_raw = str(person.get(f"TGL{y_label}", "") or "").strip()
        hdl_raw = str(person.get(f"HDL{y_label}", "") or "").strip()
        ldl_raw = str(person.get(f"LDL{y_label}", "") or "").strip()
    
        chol_result = interpret_chol(chol_raw)
        tgl_result = interpret_tgl(tgl_raw)
        hdl_result = interpret_hdl(hdl_raw)
        ldl_result = interpret_ldl(ldl_raw)
    
        summary_result = summarize_lipids(chol_raw, tgl_raw, ldl_raw)
    
        lipid_data["CHOL"].append(chol_result)
        lipid_data["TGL"].append(tgl_result)
        lipid_data["HDL"].append(hdl_result)
        lipid_data["LDL"].append(ldl_result)
        lipid_data["ผลสรุป"].append(summary_result)
    
    # แสดงตาราง
    lipid_df = pd.DataFrame.from_dict(lipid_data, orient="index", columns=[y for y in years])
    st.markdown(lipid_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: CHEST X-RAY (ผลเอกซเรย์)
    # ===============================
    
    st.markdown("### 🩻 ผลเอกซเรย์ (CXR)")
    
    # ปีที่รองรับ
    years = list(range(2561, 2569))
    
    # สร้างชื่อคอลัมน์ CXR ตามปี
    def get_cxr_col_name(year):
        return "CXR" if year == 2568 else f"CXR{str(year)[-2:]}"
    
    # ฟังก์ชันแปลผล (ถ้าค่าไม่มีให้แสดง "-")
    def interpret_cxr(value):
        if not value or str(value).strip() == "":
            return "-"
        return str(value).strip()
    
    # สร้างตารางผล
    cxr_data = []
    
    for y in years:
        col_name = get_cxr_col_name(y)
        raw_value = person.get(col_name, "")
        result = interpret_cxr(raw_value)
        cxr_data.append(result)
    
    # สร้าง DataFrame
    cxr_df = pd.DataFrame({
        "ผลเอกซเรย์": cxr_data
    }, index=years).T
    
    # แสดงผลในตาราง
    st.markdown(cxr_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: EKG (ผลคลื่นไฟฟ้าหัวใจ)
    # ===============================
    
    st.markdown("### ❤️ ผลคลื่นไฟฟ้าหัวใจ (EKG)")
    
    # ปีที่รองรับ
    years = list(range(2561, 2569))
    
    # ฟังก์ชันหาชื่อคอลัมน์ของปีนั้นๆ
    def get_ekg_col_name(year):
        return "EKG" if year == 2568 else f"EKG{str(year)[-2:]}"
    
    # ฟังก์ชันแปลผล (ถ้าไม่มีข้อมูล ให้แสดง "-")
    def interpret_ekg(value):
        if not value or str(value).strip() == "":
            return "-"
        return str(value).strip()
    
    # เตรียมข้อมูลลงตาราง
    ekg_data = []
    
    for y in years:
        col_name = get_ekg_col_name(y)
        raw_value = person.get(col_name, "")
        result = interpret_ekg(raw_value)
        ekg_data.append(result)
    
    # สร้าง DataFrame แสดงผล
    ekg_df = pd.DataFrame({
        "ผลคลื่นไฟฟ้าหัวใจ (EKG)": ekg_data
    }, index=years).T
    
    # แสดงผล
    st.markdown(ekg_df.to_html(escape=False), unsafe_allow_html=True)

    # ===============================
    # DISPLAY: ความจุปอด
    # ===============================
    st.markdown("### 🫁 สมรรถภาพปอด")

    years = list(range(2561, 2569))  # ขยายปีในอนาคตได้เลย
    
    def get_col(name: str, y: int) -> str:
        return name if y == 2568 else f"{name}{str(y)[-2:]}"
    
    def format_result(value, suffix="%"):
        try:
            val = float(value)
            return f"{val}<br><span style='font-size:13px;color:gray;'>ปกติ</span>" if val > 0 else "-"
        except:
            return "-"
    
    # เตรียมข้อมูล
    lung_data = {
        "FVC (%)": [],
        "FEV1 (%)": [],
        "FEV1/FVC (%)": [],
        "ผลสรุป": []
    }
    
    def interpret_lung(fvc, fev1, ratio):
        try:
            fvc = float(fvc)
            fev1 = float(fev1)
            ratio = float(ratio)
    
            if fvc > 80 and fev1 > 80 and ratio > 70:
                return "สมรรถภาพปอดปกติ"
            elif fvc <= 80 and fev1 > 70 and ratio <= 100:
                return "พบความผิดปกติแบบปอดจำกัดการขยายตัวเล็กน้อย"
            elif fvc <= 80 and fev1 <= 70:
                return "Mixed"
            elif fvc < 100 and fev1 <= 70 and ratio <= 65:
                return "พบความผิดปกติแบบหลอดลมอุดกั้นเล็กน้อย"
            else:
                return "สรุปไม่ได้"
        except:
            return "-"
    
    for y in years:
        y_label = "" if y == 2568 else str(y)[-2:]
    
        fvc_col = f"FVC เปอร์เซ็นต์{y_label}"
        fev1_col = f"FEV1เปอร์เซ็นต์{y_label}"
        ratio_col = f"FEV1/FVC%{y_label}"
    
        fvc_raw = str(person.get(fvc_col, "") or "").strip()
        fev1_raw = str(person.get(fev1_col, "") or "").strip()
        ratio_raw = str(person.get(ratio_col, "") or "").strip()
  
        # แสดงค่าพร้อมแปลผล
        fvc_display = format_result(fvc_raw)
        fev1_display = format_result(fev1_raw)
        ratio_display = format_result(ratio_raw)
    
        # สรุปสมรรถภาพปอด
        summary = interpret_lung(fvc_raw, fev1_raw, ratio_raw)
    
        lung_data["FVC (%)"].append(fvc_display)
        lung_data["FEV1 (%)"].append(fev1_display)
        lung_data["FEV1/FVC (%)"].append(ratio_display)
        lung_data["ผลสรุป"].append(summary)
    
    # แสดงตาราง
    lung_df = pd.DataFrame.from_dict(lung_data, orient="index", columns=years)
    st.markdown(lung_df.to_html(escape=False), unsafe_allow_html=True)


