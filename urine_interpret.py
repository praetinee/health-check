value = value.strip().lower()

def interpret_alb(value):
    if not value:
        return "-"
    value = value.strip().lower()

    if value == "negative":
        return "ไม่พบ"
    elif value in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif value == "3+":
        return "พบโปรตีนในปัสสาวะ"
    return "-"

def interpret_sugar(value):
    if not value:
        return "-"
    value = value.strip().lower()

    if value == "negative":
        return "ไม่พบ"
    elif value == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif value in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสสาวะ"
    return "-"

value = value.strip().lower()

def interpret_rbc(value):
    if not value:
        return "-"
    value = value.strip().lower()

    if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif value in ["5-10", "10-20"]:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    if not value:
        return "-"
    value = value.strip().lower()

    if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif value in ["5-10", "10-20"]:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"

def summarize_urine(*results):
    if all(r in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"] for r in results):
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

    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_text and wbc_text == "ปกติ":
        return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"

    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_text and wbc_text == "ปกติ":
        return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"

    if "พบเม็ดเลือดขาวในปัสสาวะ" in wbc_text and "เล็กน้อย" not in wbc_text:
        return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"

    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"

