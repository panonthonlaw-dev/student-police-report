import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random
import requests
import os
from fpdf import FPDF

# --- ฟังก์ชันโหลดฟอนต์ไทยอัตโนมัติ (ไม่ต้องสร้างโฟลเดอร์) ---
def get_thai_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Regular.ttf" # ใช้ฟอนต์มาตรฐานที่รองรับไทยจาก Google
    font_path = "ThaiFont.ttf"
    if not os.path.exists(font_path):
        response = requests.get(font_url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# --- ฟังก์ชันสร้าง PDF ---
def create_pdf(row_data):
    pdf = FPDF()
    pdf.add_page()
    
    font_path = get_thai_font()
    
    # ลงทะเบียนฟอนต์ที่โหลดมา
    pdf.add_font('ThaiFont', '', font_path)
    pdf.set_font('ThaiFont', '', 16)
    
    # เนื้อหาใน PDF
    pdf.cell(190, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('ThaiFont', '', 14)
    pdf.cell(190, 10, txt=f"เลขที่รับแจ้ง: {row_data['Report_ID']}", ln=True)
    pdf.cell(190, 10, txt=f"วันเวลา: {row_data['Timestamp']}", ln=True)
    pdf.cell(190, 10, txt=f"ประเภทเหตุ: {row_data['Incident_Type']}", ln=True)
    pdf.cell(190, 10, txt=f"สถานที่: {row_data['Location']}", ln=True)
    pdf.multi_cell(0, 10, txt=f"รายละเอียด: {row_data['Details']}")
    pdf.ln(5)
    pdf.set_font('ThaiFont', '', 16)
    pdf.cell(190, 10, txt=f"สถานะ: {row_data['Status']}", ln=True)
    pdf.set_font('ThaiFont', '', 14)
    pdf.multi_cell(0, 10, txt=f"บันทึกการจัดการ: {row_data.get('Action_Details', '-')}")
    pdf.cell(190, 10, txt=f"ผู้รับผิดชอบ: {row_data.get('Handled_By', '-')}", ln=True)
    
    return pdf.output()

# --- 📋 ส่วนของหน้าจอ Dashboard (เฉพาะจุดที่แก้ไขสถานะ) ---
# (ก๊อปปี้ไปวางในส่วนบันทึกข้อมูลใน officer_dashboard)
if st.button("💾 บันทึกการดำเนินงาน", type="primary", use_container_width=True):
    df.at[row_idx, 'Status'] = new_status
    df.at[row_idx, 'Action_Details'] = action_detail
    df.at[row_idx, 'Handled_By'] = user['name']
    
    # อัปเดตลง Google Sheets
    conn.update(data=df)
    
    # แสดงข้อความแจ้งเตือนบันทึกสำเร็จ
    st.success(f"📌 บันทึกข้อมูลของเลขที่ {selected_id} เรียบร้อยแล้ว!")
    st.toast("บันทึกสำเร็จ!", icon="✅")
    st.rerun() # สั่งรีเฟรชหน้าเพื่อให้ข้อมูลในตารางอัปเดตทันที
