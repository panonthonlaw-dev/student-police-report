import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random
import os
from fpdf import FPDF

# --- 1. ตั้งค่าหน้าจอและเวลา ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

def get_now():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

# --- 🛠️ ฟังก์ชันจัดการข้อมูลว่าง (ป้องกันคำว่า nan) ---
def clean_val(val):
    if pd.isna(val) or val == "nan":
        return ""
    return str(val)

# --- 🔑 2. ระบบจัดการเซสชันและ Timeout ---
# กำหนดเวลาหมดอายุ (30 นาที)
TIMEOUT_SECONDS = 30 * 60 

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = get_now()

# ตรวจสอบ Timeout (ถ้ามีการล็อกอินอยู่)
if st.session_state.current_user:
    now = get_now()
    elapsed = (now - st.session_state.last_activity).total_seconds()
    if elapsed > TIMEOUT_SECONDS:
        st.session_state.current_user = None
        st.warning("⚠️ เซสชันหมดอายุเนื่องจากไม่มีการใช้งานนานเกิน 30 นาที กรุณาล็อกอินใหม่")
        st.rerun()
    else:
        # อัปเดตเวลาที่มีกิจกรรมล่าสุด
        st.session_state.last_activity = now

# --- (ข้ามส่วน OFFICER_ACCOUNTS และ create_pdf ไปยังส่วน UI บันทึกผล) ---
OFFICER_ACCOUNTS = {
    "Patwit1510": {"name": "แอดมินสูงสุด", "role": "admin"},
    "Pencharee001": {"name": "ครูเพ็ญชรีย์ (ปกครอง)", "role": "admin"},
    "Chaiya001": {"name": "ครูไชยา(ปกครอง)", "role": "admin"},
    "Jak001": {"name": "ยามจักร (รปภ.)", "role": "admin"},
    "User01": {"name": "ผู้กำกับ(ตำรวจนักเรียน)", "role": "admin"},
    "User02": {"name": "รองผู้กำกับจราจร(ตำรวจนักเรียน)", "role": "admin"},
    "User03": {"name": "ครูเวร (ตรวจการณ์)", "role": "viewer"},
    "User04": {"name": "ตำรวจนักเรียน", "role": "viewer"}
}

# [ฟังก์ชัน create_pdf คงเดิมจากเวอร์ชันก่อนหน้า]
def create_pdf(row_data):
    # ... (โค้ดเดิม) ...
    return None # ใส่เพื่อให้โครงสร้างครบ

# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### 🏢 ระบบจัดการ (คุณ{user['name']})")
    with col2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl=0)
        tab1, tab2 = st.tabs(["🔎 รายการทั้งหมด", "🛠 สอบสวนและบันทึกผล"])

        with tab2:
            if user['role'] == 'admin':
                ids = df['Report_ID'].dropna().unique().tolist()
                sid = st.selectbox("เลือกเลขที่รับแจ้ง", ids)
                sel = df[df['Report_ID'] == sid]
                
                if not sel.empty:
                    idx = sel.index[0]
                    row = sel.iloc[0]
                    with st.container(border=True):
                        st.write("📋 **บันทึกการสอบสวนเพิ่มเติม**")
                        c1, c2 = st.columns(2)
                        with c1:
                            # ใช้ clean_val เพื่อลบ nan และใส่ placeholder แทน
                            v_victim = st.text_input("ผู้เสียหาย", value=clean_val(row.get('Victim')), placeholder="ระบุชื่อผู้เสียหาย...")
                            v_accused = st.text_input("ผู้ถูกกล่าวหา", value=clean_val(row.get('Accused')), placeholder="ระบุชื่อผู้ถูกกล่าวหา...")
                            v_witness = st.text_input("พยาน", value=clean_val(row.get('Witness')), placeholder="ระบุชื่อพยาน (ถ้ามี)...")
                        with c2:
                            v_teacher = st.text_input("ครูผู้สอบสวน", value=clean_val(row.get('Teacher_Investigator')), placeholder="ระบุชื่อครูผู้รับผิดชอบ...")
                            v_student = st.text_input("ตำรวจนักเรียนสอบสวน", value=clean_val(row.get('Student_Police_Investigator')), placeholder="ระบุชื่อตำรวจนักเรียน...")
                            status_opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                            v_status = st.selectbox("สถานะจัดการ", status_opts, index=status_opts.index(row['Status']) if row['Status'] in status_opts else 0)
                        
                        v_statement = st.text_area("บันทึกคำให้การ/รายละเอียดการดำเนินการ", value=clean_val(row.get('Statement')), placeholder="สรุปเนื้อหาการสอบสวนที่นี่...")

                        if st.button("💾 บันทึกข้อมูลการสอบสวน", type="primary", use_container_width=True):
                            df.at[idx, 'Victim'] = v_victim
                            df.at[idx, 'Accused'] = v_accused
                            df.at[idx, 'Witness'] = v_witness
                            df.at[idx, 'Teacher_Investigator'] = v_teacher
                            df.at[idx, 'Student_Police_Investigator'] = v_student
                            df.at[idx, 'Status'] = v_status
                            df.at[idx, 'Statement'] = v_statement
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("บันทึกข้อมูลเรียบร้อย!")
                            st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 4. หน้าจอหลักและการล็อกอิน ---
def main_page():
    st.markdown("<h1 style='text-align: center;'>👮‍♂️ ระบบแจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    # ... (ส่วนแจ้งเหตุเดิม) ...

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        input_pwd = st.text_input("รหัสผ่าน", type="password", key="login_pwd")
        if st.button("เข้าสู่ระบบ"):
            if input_pwd in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[input_pwd]
                st.session_state.last_activity = get_now()
                st.success(f"ยินดีต้อนรับคุณ {OFFICER_ACCOUNTS[input_pwd]['name']}")
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง")

# --- 🚀 5. รันแอป ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
