# --- ฟังก์ชันโหลดฟอนต์ไทยอัตโนมัติ (Sarabun จาก Google) ---
@st.cache_data
def get_thai_font():
    # ใช้ Noto Sans Thai หรือ Sarabun ที่เสถียร
    font_url = "https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai-Regular.ttf"
    font_path = "ThaiFont.ttf"
    if not os.path.exists(font_path):
        try:
            response = requests.get(font_url, timeout=10)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
                return font_path
        except Exception as e:
            st.error(f"โหลดฟอนต์ไม่สำเร็จ: {e}")
            return None
    return font_path

# --- ฟังก์ชันสร้าง PDF (ฉบับแก้ไขตัวหนังสือหาย) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        font_p = get_thai_font()
        
        if font_p and os.path.exists(font_p):
            pdf.add_font('ThaiFont', '', font_p)
            pdf.set_font('ThaiFont', '', 18)
        else:
            # ถ้าโหลดฟอนต์ไม่ได้ ให้ใช้ Arial (แต่ไทยจะไม่ออก)
            pdf.set_font('Arial', '', 12)

        # ส่วนหัวเอกสาร
        pdf.cell(pdf.epw, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
        pdf.ln(10)
        
        # ปรับฟอนต์สำหรับเนื้อหา
        if font_p: pdf.set_font('ThaiFont', '', 14)

        # บันทึกข้อมูลทีละบรรทัด (ใช้คำภาษาไทยได้เลย)
        pdf.cell(pdf.epw, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"วันเวลาแจ้ง: {row_data.get('Timestamp', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"สถานที่: {row_data.get('Location', '-')}", ln=True)
        
        pdf.ln(5)
        pdf.multi_cell(pdf.epw, 10, txt=f"รายละเอียดเหตุการณ์: {row_data.get('Details', '-')}")
        
        pdf.ln(5)
        if font_p: pdf.set_font('ThaiFont', '', 16)
        pdf.cell(pdf.epw, 10, txt=f"สถานะการจัดการ: {row_data.get('Status', '-')}", ln=True)
        
        if font_p: pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(pdf.epw, 10, txt=f"บันทึกการดำเนินการ: {row_data.get('Action_Details', '-')}")
        pdf.cell(pdf.epw, 10, txt=f"เจ้าหน้าที่ผู้ดำเนินการ: {row_data.get('Handled_By', '-')}", ln=True)
        
        return pdf.output()
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการสร้าง PDF: {str(e)}".encode('utf-8')
