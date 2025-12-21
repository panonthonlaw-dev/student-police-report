import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. การตั้งค่าหน้าจอและซ่อน UI ที่ไม่จำเป็น (GitHub, Header, Footer)
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="centered")

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

# 2. จัดการสถานะการ Login ด้วย Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- ฟังก์ชันสำหรับหน้าเจ้าหน้าที่ ---
def admin_page():
    st.title("📋 รายงานสำหรับเจ้าหน้าที่")
    if st.button("⬅️ กลับหน้าหลัก"):
        st.session_state.logged_in = False
        st.rerun()
    
    try:
        df = conn.read()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ดาวน์โหลดรายงาน (CSV)", data=csv, file_name="report.csv")
        else:
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุ")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- ฟังก์ชันสำหรับหน้าแจ้งเหตุ (นักเรียน) ---
def main_page():
    st.title("👮‍♂️ ระบบแจ้งเหตุ - สารวัตรนักเรียน")
    st.subheader("โรงเรียนโพนทองพัฒนาวิทยา")
    
    with st.form(key="incident_form"):
        reporter = st.text_input("ชื่อผู้แจ้ง (ระบุหรือไม่ก็ได้)")
        incident_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด/บุหรี่", "พฤติกรรมชู้สาว", "หนีเรียน", "อื่นๆ"])
        location = st.text_input("สถานที่เกิดเหตุ")
        details = st.text_area("รายละเอียด")
        submit = st.form_submit_button("ส่งข้อมูลแจ้งเหตุ")

    if submit:
        if location and details:
            existing_data = conn.read()
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
                "Incident_Type": incident_type,
                "Location": location,
                "Details": details,
                "Status": "รอดำเนินการ"
            }])
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
            st.balloons()
        else:
            st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

    # --- ส่วน Login ของเจ้าหน้าที่ อยู่ล่างสุด ---
    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        admin_pass = st.text_input("กรอกรหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            # เปลี่ยนรหัสผ่านตรงนี้หรือใช้ st.secrets["admin_password"]
            if admin_pass == "admin_patwit": 
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# --- ส่วนตัดสินใจว่าจะแสดงหน้าไหน ---
if st.session_state.logged_in:
    admin_page()
else:
    main_page()
