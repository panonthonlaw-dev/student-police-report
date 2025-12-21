import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="แจ้งเหตุสารวัตรนักเรียน", page_icon="👮‍♂️")

st.title("👮‍♂️ ระบบแจ้งเหตุ - สารวัตรนักเรียน")
st.write("โรงเรียนโพนทองพัฒนาวิทยา")

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ฟอร์มรับข้อมูล
with st.form(key="incident_form"):
    reporter = st.text_input("ชื่อผู้แจ้ง (ระบุหรือไม่ก็ได้)")
    incident_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
    location = st.text_input("สถานที่เกิดเหตุ")
    details = st.text_area("รายละเอียด")
    
    submit = st.form_submit_button("ส่งข้อมูล")

if submit:
    if not location or not details:
        st.warning("กรุณากรอกสถานที่และรายละเอียด")
    else:
        # ดึงข้อมูลเดิม
        existing_data = conn.read()
        
        # สร้างข้อมูลใหม่
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
            "Incident_Type": incident_type,
            "Location": location,
            "Details": details,
            "Status": "รอดำเนินการ"
        }])
        
        # รวมข้อมูลและอัปเดต
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(data=updated_df)
        
        st.success("ส่งข้อมูลสำเร็จ! ข้อมูลถูกส่งไปยังหน่วยสารวัตรนักเรียนแล้ว")
        st.balloons()
