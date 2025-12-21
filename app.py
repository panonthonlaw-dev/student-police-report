# --- 📄 ฟังก์ชันสร้าง PDF (แก้ไขจุดที่ทำให้เกิด Unicode Error) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        font_path = "THSarabunNew.ttf"
        
        if os.path.exists(font_path):
            pdf.add_font('THSarabun', '', font_path)
            pdf.set_font('THSarabun', '', 18)
            
            # เนื้อหา PDF
            pdf.cell(pdf.epw, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font('THSarabun', '', 14)
            pdf.cell(pdf.epw, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=True)
            pdf.cell(pdf.epw, 10, txt=f"วันเวลาแจ้ง: {row_data.get('Timestamp', '-')}", ln=True)
            pdf.cell(pdf.epw, 10, txt=f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')}", ln=True)
            pdf.cell(pdf.epw, 10, txt=f"สถานที่: {row_data.get('Location', '-')}", ln=True)
            pdf.ln(5)
            pdf.multi_cell(pdf.epw, 10, txt=f"รายละเอียด: {row_data.get('Details', '-')}")
            pdf.ln(5)
            pdf.set_font('THSarabun', '', 16)
            pdf.cell(pdf.epw, 10, txt=f"สถานะ: {row_data.get('Status', '-')}", ln=True)
            pdf.set_font('THSarabun', '', 14)
            pdf.multi_cell(pdf.epw, 10, txt=f"บันทึกการจัดการ: {row_data.get('Action_Details', '-')}")
            pdf.cell(pdf.epw, 10, txt=f"ผู้ดำเนินการ: {row_data.get('Handled_By', '-')}", ln=True)
            
            # คืนค่าเป็น bytes โดยตรง (ไม่ต้อง decode)
            return pdf.output()
        else:
            return "FileNotFound" # ส่งเป็น String ปกติถ้าหาไฟล์ไม่เจอ
            
    except Exception as e:
        return f"Error: {str(e)}" # ส่งข้อความ Error เป็น String

# --- 📋 ส่วนการแสดงผลใน Dashboard (Tab 2) ---
# แก้ไขจุดการเช็คค่าเพื่อให้ไม่เกิด Error ตอนรัน
if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
    df.at[idx, 'Status'] = new_st
    df.at[idx, 'Action_Details'] = act_detail
    df.at[idx, 'Handled_By'] = user['name']
    conn.update(data=df)
    st.success(f"บันทึกเลขที่ {sid} สำเร็จ!")
    st.rerun()

# ส่วนการสร้างปุ่มดาวน์โหลด PDF
pdf_result = create_pdf(row)

if isinstance(pdf_result, (bytes, bytearray)):
    # ถ้าได้ข้อมูลไฟล์มา (Bytes) ให้แสดงปุ่มโหลด
    st.download_button(
        label="📥 ดาวน์โหลด PDF สรุปงาน",
        data=pdf_result,
        file_name=f"Report_{sid}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
elif pdf_result == "FileNotFound":
    st.error("❌ หาไฟล์ THSarabunNew.ttf ใน GitHub ไม่เจอ")
else:
    # ถ้าเป็น String อื่นๆ คือข้อความ Error
    st.error(f"⚠️ ไม่สามารถสร้าง PDF ได้: {pdf_result}")
