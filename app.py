def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        font_path = "THSarabunNew.ttf"
        if not os.path.exists(font_path):
            return "MISSING_FONT"

        # ลงทะเบียนฟอนต์ (Regular และ Bold ถ้ามีไฟล์)
        pdf.add_font('ThaiFont', '', font_path)
        pdf.add_font('ThaiFontBold', '', font_path) # ใช้ไฟล์เดิมแต่ตั้งชื่อแยกเพื่อทำตัวหนาจำลอง
        
        # --- 1. หัวกระดาษ (Header) ---
        pdf.set_font('ThaiFont', '', 20)
        pdf.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการ", ln=True, align='C')
        
        # เส้นคั่นหัวกระดาษ
        pdf.line(10, 32, 200, 32)
        pdf.ln(10)

        # --- 2. ส่วนข้อมูลทั่วไป (General Info) ---
        pdf.set_font('ThaiFont', '', 15)
        
        # เลขที่รับแจ้งและวันที่ (จัดให้อยู่บรรทัดเดียวกันแบบสวยงาม)
        col_width = pdf.epw / 2
        pdf.cell(col_width, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=0)
        pdf.cell(col_width, 10, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", ln=1, align='R')
        
        pdf.cell(0, 10, txt=f"ประเภทเหตุการณ์: {row_data.get('Incident_Type', '-')}", ln=True)
        pdf.cell(0, 10, txt=f"สถานที่เกิดเหตุ: {row_data.get('Location', '-')}", ln=True)
        pdf.cell(0, 10, txt=f"ชื่อผู้แจ้งเหตุ: {row_data.get('Reporter', 'ไม่ประสงค์ออกนาม')}", ln=True)
        
        # เส้นคั่นส่วนที่ 1
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # --- 3. รายละเอียดเหตุการณ์ (Incident Details) ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="รายละเอียดเหตุการณ์:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(0, 8, txt=row_data.get('Details', '-'))
        pdf.ln(5)

        # --- 4. ผลการดำเนินงาน (Action Taken) ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ผลการดำเนินการของเจ้าหน้าที่:", ln=True)
        
        # สร้างกล่องสีเทาอ่อนสำหรับใส่ผลการดำเนินงาน
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font('ThaiFont', '', 14)
        
        status_text = f"สถานะปัจจุบัน: {row_data.get('Status', '-')}"
        action_text = f"รายละเอียดการจัดการ: {row_data.get('Action_Details', '-')}"
        
        pdf.multi_cell(0, 10, txt=f"{status_text}\n{action_text}", border=1, fill=True)
        pdf.ln(15)

        # --- 5. ส่วนลงนาม (Signatures) ---
        pdf.set_font('ThaiFont', '', 14)
        current_y = pdf.get_y()
        
        # ฝั่งซ้าย: เจ้าหน้าที่ผู้บันทึก
        pdf.set_xy(10, current_y)
        pdf.cell(90, 10, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 10, txt=f"( {row_data.get('Handled_By', '.................................')} )", ln=True, align='C')
        pdf.cell(90, 8, txt="เจ้าหน้าที่สารวัตรนักเรียนผู้ดำเนินการ", ln=True, align='C')
        
        # ฝั่งขวา: หัวหน้าฝ่าย/อาจารย์
        pdf.set_xy(110, current_y)
        pdf.cell(90, 10, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 10, txt="(..........................................................)", ln=True, align='C')
        pdf.cell(90, 8, txt="อาจารย์ที่ปรึกษา/หัวหน้างานปกครอง", ln=True, align='C')

        return pdf.output()
        
    except Exception as e:
        return f"ERROR: {str(e)}"
