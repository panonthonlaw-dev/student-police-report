import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. ตั้งค่าหน้าจอและซ่อน UI
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. จัดการสถานะการ Login และ Role
if 'role' not in st.session_state:
    st.session_state.role = None  # None, 'admin', 'high_officer', 'general_officer'

# --- ฟังก์ชันการจัดการข้อมูล (ลบ/แก้ไข) ---
def update_database(df):
    try:
        conn.update(data=df)
        st.success("✅ อัปเดตข้อมูลในฐานข้อมูลเรียบร้อย")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปเดต: {e}")

# --- หน้าจอสำหรับเจ้าหน้าที่ (Admin/Officer Dashboard) ---
def officer_page():
    role = st.session_state.role
    st.title(f"📋 ระบบจัดการข้อมูล - ระดับ: {role}")
    
    if st.button("⬅️ ออกจากระบบ"):
        st.session_state.role = None
        st.rerun()

    try:
        df = conn.read()
        if df.empty:
            st.info("ไม่มีข้อมูลการแจ้งเหตุ")
            return

        # --- ส่วนที่ 1: การดูข้อมูล (ทำได้ทุกคน) ---
        st.subheader("ข้อมูลเหตุการณ์ทั้งหมด")
        st.dataframe(df, use_container_width=True)

        # --- ส่วนที่ 2: การจัดการสถานะ (เจ้าหน้าที่ระดับสูงขึ้นไป) ---
        if role in ['admin', 'high_officer']:
            st.markdown("---")
            st.subheader("🛠 จัดการสถานะเหตุการณ์")
            row_to_edit = st.selectbox("เลือกรายการที่ต้องการเปลี่ยนสถานะ (อ้างอิงลำดับ)", df.index)
            new_status = st.selectbox("เปลี่ยนสถานะเป็น", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"])
            
            if st.button("บันทึกการเปลี่ยนสถานะ"):
                df.at[row_to_edit, 'Status'] = new_status
                update_database(df)

        # --- ส่วนที่ 3: การลบข้อมูล (แอดมินสูงสุดเท่านั้น) ---
        if role == 'admin':
            st.markdown("---")
            st.subheader("🚨 ส่วนเฉพาะแอดมิน (ลบข้อมูล)")
            row_to_delete = st.number_input("ใส่หมายเลขแถวที่ต้องการลบ", min_value=0, max_value=len(df)-1, step=1)
            if st.button("🗑 ลบข้อมูลแถวนี้แบบถาวร", type="primary"):
                df = df.drop(df.index[row_to_delete])
                update_database(df)

    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")

# --- หน้าจอสำหรับนักเรียน (Public Form) ---
def main_page():
    st.title("👮‍♂️ แจ้งเหตุสารวัตรนักเรียน")
    st.subheader("โรงเรียนโพนทองพัฒนาวิทยา")
    
    with st.form(key="report_form"):
        reporter = st.text_input("ชื่อผู้แจ้ง (ระบุหรือไม่ก็ได้)")
        incident_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด/บุหรี่", "พฤติกรรมชู้สาว", "หนีเรียน", "อื่นๆ"])
        location = st.text_input("สถานที่เกิดเหตุ")
        details = st.text_area("รายละเอียด")
        submit = st.form_submit_button("ส่งข้อมูล")

    if submit and location and details:
        df_old = conn.read()
        new_data = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
            "Incident_Type": incident_type,
            "Location": location,
            "Details": details,
            "Status": "รอดำเนินการ"
        }])
        updated_df = pd.concat([df_old, new_data], ignore_index=True)
        conn.update(data=updated_df)
        st.success("ส่งข้อมูลสำเร็จ")
        st.balloons()

    # --- ส่วน Login ท้ายหน้า ---
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pwd = st.text_input("รหัสผ่านสารวัตรนักเรียน", type="password")
        if st.button("เข้าสู่ระบบ"):
            # กำหนดรหัสผ่านตรงนี้
            if pwd == "admin99": # แอดมินสูงสุด
                st.session_state.role = 'admin'
                st.rerun()
            elif pwd == "boss88": # เจ้าหน้าที่ระดับสูง
                st.session_state.role = 'high_officer'
                st.rerun()
            elif pwd == "staff77": # เจ้าหน้าที่ทั่วไป
                st.session_state.role = 'general_officer'
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# ตรวจสอบว่าต้องแสดงหน้าไหน
if st.session_state.role:
    officer_page()
else:
    main_page()
