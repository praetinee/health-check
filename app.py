# ส่วนต้นเหมือนเดิม ...

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

if "person_data" in st.session_state:
    person = st.session_state["person_data"]
    st.success(f"✅ พบข้อมูลของ: {person['ชื่อ-สกุล']}")
    st.markdown(f"**HN:** {person['HN']}  \n**เลขบัตรประชาชน:** {person['เลขบัตรประชาชน']}  \n**เพศ:** {person.get('เพศ', '-')}")

    # ปีที่มีในข้อมูล
    available_years = sorted(set(
        int(re.search(r'(\d{2})$', col).group(1)) 
        for col in df.columns 
        if re.search(r'น้ำหนัก\d{2}$', col)
    ), reverse=True)

    year_display = {f"พ.ศ. 25{y}": y for y in available_years}
    selected_label = st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผล", list(year_display.keys()))
    selected_year = year_display[selected_label]

    # ดึงค่าตามปี
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
    - **Year (B.E.):** 25{selected_year}  
    - **Weight:** {weight} kg  
    - **Height:** {height} cm  
    - **Waist:** {waist} cm ({assess_waist(waist)})  
    - **BMI:** {bmi_text} ({interpret_bmi(bmi)})  
    - **Blood Pressure:** {sbp}/{dbp} mmHg ({interpret_bp(sbp, dbp)})  
    - **Pulse:** {pulse} bpm
    """)

    # ===============================
    # สรุปผลสุขภาพหลายปี (ตารางแนวนอน)
    # ===============================
    summary_data = {}
    for y in available_years:
        summary_data[f"25{y}"] = {
            "Weight (kg)": person.get(f"น้ำหนัก{y}", "-"),
            "Height (cm)": person.get(f"ส่วนสูง{y}", "-"),
            "Waist (cm)": person.get(f"รอบเอว{y}", "-"),
            "BMI": calc_bmi(person.get(f"น้ำหนัก{y}", "-"), person.get(f"ส่วนสูง{y}", "-")),
            "Blood Pressure": f"{person.get(f'SBP{y}', '-')}/{person.get(f'DBP{y}', '-')}",
            "Pulse": person.get(f"pulse{y}", "-")
        }

    summary_df = pd.DataFrame(summary_data)
    st.markdown("### 📊 Health Summary (Transposed View)")
    st.dataframe(summary_df)

    # ===============================
    # แนวโน้ม BMI (ใช้ภาษาอังกฤษ)
    # ===============================
    st.markdown("### 📈 BMI Trend Over Years")
    bmi_values = [calc_bmi(person.get(f"น้ำหนัก{y}", "-"), person.get(f"ส่วนสูง{y}", "-")) for y in available_years]
    years_labels = [f"25{y}" for y in available_years]

    fig, ax = plt.subplots()
    ax.plot(years_labels, bmi_values, marker='o', linestyle='-')
    ax.set_title("BMI Trend")
    ax.set_xlabel("Year (B.E.)")
    ax.set_ylabel("BMI")
    st.pyplot(fig)
