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

# 2. ฐานข้อมูลผู้ใช้งาน (คุณครูเพิ่มชื่อและรหัสผ่านตรงนี้ได้ไม่จำกัดครับ)
# รูปแบบคือ  "รหัสผ่าน": {"name": "ชื่อผู้ใช้", "role": "ระดับสิทธิ์"}
USER_DB = {
    # ระดับ 1: แอดมินสูงสุด (แนะนำให้มีคนเดียว หรือเฉพาะคนสำคัญ)
    "admin_master": {"name": "อาจารย์หัวหน้าฝ่ายปกครอง", "role": "admin"},
    
    # ระดับ 2: เจ้าหน้าที่ระดับสูง (เพิ่มได้หลายคน รหัสห้ามซ้ำกัน)
    "boss_kong": {"name": "สารวัตรก้อง", "role": "high_officer"},
    "boss_fah": {"name": "สารวัตรฟ้า", "role": "high_officer"},
    
    # ระดับ 3: เจ้าหน้าที่ทั่วไป (เพิ่มได้หลายคน)
    "staff_01": {"name": "นายสมชาย (เวรจันทร์)", "role": "general_officer"},
    "staff_02": {"name": "นางสาวสมหญิง (เวรอังคาร)", "role": "general_officer"},
    "staff_test": {"name": "เจ้าหน้าที่ทดสอบ", "role": "general_officer"},
}

# 3. จัดการสถานะการ Login ใน Session
if 'user_info' not in st.session_state:
    st.session_state.user_info = None  # จะเก็บข้อมูลคนลาอกอิน

# --- ฟังก์ชันอัปเดตข้อมูล ---
def update_database(df):
    try:
        conn.update(data=df)
        st.success("✅ อัปเดตข้อมูลสำเร็จ")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- หน้าจอสำหรับเจ้าหน้าที่ ---
def officer_page():
    user = st.session_state.user_info
    st.title(f"📋 ระบบจัดการข้อมูล")
    st.info(f"👤 ผู้ใช้งานปัจจุบัน: **{user['name']}** | สิทธิ์: **{user['role']}**")
    
    if st.button("⬅️ ออกจากระบบ"):
        st.session_state.user_info = None
        st.rerun()

    try:
        df = conn.read()
        if df.empty:
            st.info("ยังไม่มีข้อมูลแจ้งเหตุ")
            return

        st.subheader("รายการแจ้งเหตุทั้งหมด")
        st.dataframe(df, use_container_width=True)

        # สิทธิ์ระดับ High Officer หรือ Admin ขึ้นไป (เปลี่ยนสถานะได้)
        if user['role'] in ['admin', 'high_officer']:
            st.markdown("---")
            st.subheader("🛠 จัดการสถานะ (สำหรับระดับสูง)")
            row_idx = st.selectbox("เลือกลำดับเหตุการณ์", df.index)
            status_list = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
            new_status = st.selectbox("เปลี่ยนเป็น", status_list, index=status_list.index(df.at[row_idx, 'Status']) if df.at[row_idx, 'Status'] in status_list else 0)
            
            if st.button("บันทึกการเปลี่ยนแปลง"):
                df.at[row_idx, 'Status'] = new_status
                # แถม: บันทึกด้วยว่าใครเป็นคนมาแก้ล่าสุด (ถ้ามีคอลัมน์ใน Sheets)
                # df.at[row_idx, 'LastModifiedBy'] = user['name'] 
                update_database(df)

        # สิทธิ์ระดับ Admin เท่านั้น (ลบข้อมูลได้)
        if user['role'] == 'admin':
            st.markdown("---")
            st.subheader("🚨 ส่วนงานแอดมินสูงสุด")
            row_del = st.number_input("ลำดับแถวที่ต้องการลบ", min_value=0, max_value=len(df)-1, step=1)
            if st.button("🗑 ลบข้อมูลถาวร", type="primary"):
                df = df.drop(df.index[row_del])
                update_database(df)

    except Exception as e:
        st.error(f"ดึงข้อมูลไม่ได้: {e}")

# --- หน้าจอแจ้งเหตุ (นักเรียน) ---
def main_page():
    st.title("👮‍♂️ แจ้งเหตุสารวัตรนักเรียน")
    st.write("โรงเรียนโพนทองพัฒนาวิทยา")
    
    with st.form(key="report"):
        reporter = st.text_input("ชื่อผู้แจ้ง (ระบุหรือไม่ก็ได้)")
        i_type = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
        loc = st.text_input("สถานที่")
        det = st.text_area("รายละเอียด")
        submit = st.form_submit_button("ส่งข้อมูล")

    if submit and loc and det:
        df_old = conn.read()
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
            "Incident_Type": i_type,
            "Location": loc,
            "Details": det,
            "Status": "รอดำเนินการ"
        }])
        updated_df = pd.concat([df_old, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("ส่งข้อมูลสำเร็จ")
        st.balloons()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 เข้าสู่ระบบเจ้าหน้าที่"):
        input_pwd = st.text_input("รหัสผ่านประจำตัว", type="password")
        if st.button("Login"):
            if input_pwd in USER_DB:
                st.session_state.user_info = USER_DB[input_pwd]
                st.success(f"ยินดีต้อนรับคุณ {USER_DB[input_pwd]['name']}")
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# ตรวจสอบการแสดงผล
if st.session_state.user_info:
    officer_page()
else:
    main_page()
