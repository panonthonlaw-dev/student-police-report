import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอและซ่อน UI ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ระบบจัดการสิทธิ์ (จัดการง่ายที่นี่) ---
# คุณครูสามารถเพิ่ม/ลบ รายชื่อหรือเปลี่ยนรหัสผ่านได้ที่ส่วนนี้เลยครับ
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

# --- 3. จัดการ Session การเข้าสู่ระบบ ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- ฟังก์ชันอัปเดตฐานข้อมูล ---
def update_db(df):
    try:
        conn.update(data=df)
        st.success("✅ บันทึกการเปลี่ยนแปลงเรียบร้อย")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- หน้าจอสำหรับเจ้าหน้าที่ (Officer Dashboard) ---
def officer_dashboard():
    user = st.session_state.current_user
    st.title(f"📋 ระบบจัดการเหตุการณ์ ({user['name']})")
    
    if st.button("⬅️ ออกจากระบบ"):
        st.session_state.current_user = None
        st.rerun()

    try:
        df = conn.read()
        if df.empty:
            st.info("ไม่มีข้อมูลการแจ้งเหตุ")
            return

        # --- ตารางข้อมูล (เห็นทุกคน) ---
        st.subheader("รายการแจ้งเหตุทั้งหมด")
        st.dataframe(df, use_container_width=True)

        # --- ส่วนที่ 1: การแก้ไขสถานะ (สิทธิ์ Admin ทำได้) ---
        if user['role'] == 'admin':
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🛠 จัดการสถานะเหตุการณ์")
                row_to_edit = st.selectbox("เลือกรายการ (ลำดับแถว)", df.index)
                new_status = st.selectbox("เปลี่ยนสถานะเป็น", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"])
                if st.button("บันทึกสถานะ"):
                    df.at[row_to_edit, 'Status'] = new_status
                    update_db(df)
            
            with col2:
                st.subheader("🚨 ลบข้อมูล (ระมัดระวัง)")
                row_to_del = st.number_input("ลำดับแถวที่ต้องการลบ", min_value=0, max_value=len(df)-1, step=1)
                if st.button("🗑 ลบข้อมูลถาวร", type="primary"):
                    df = df.drop(df.index[row_del])
                    update_db(df)
        
        # --- ส่วนที่ 2: สิทธิ์ Viewer (ดูได้อย่างเดียว) ---
        elif user['role'] == 'viewer':
            st.warning("🔒 คุณมีสิทธิ์ 'เข้าชม' เท่านั้น ไม่สามารถแก้ไขข้อมูลได้")

    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลจาก Sheets ได้: {e}")

# --- หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.title("👮‍♂️ แจ้งเหตุสารวัตรนักเรียน")
    st.write("โรงเรียนโพนทองพัฒนาวิทยา")

    with st.form(key="incident_form"):
        reporter = st.text_input("ชื่อผู้แจ้ง (ระบุหรือไม่ก็ได้)")
        i_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
        loc = st.text_input("สถานที่เกิดเหตุ")
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
        st.success("ส่งข้อมูลสำเร็จ! ข้อมูลถูกส่งไปยังหน่วยสารวัตรนักเรียนแล้ว")
        st.balloons()

    # --- ส่วน Login ล่างสุด ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        input_pwd = st.text_input("รหัสผ่านประจำตัว", type="password")
        if st.button("เข้าสู่ระบบ"):
            if input_pwd in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[input_pwd]
                st.success(f"ยินดีต้อนรับคุณ {OFFICER_ACCOUNTS[input_pwd]['name']}")
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# เลือกว่าจะแสดงหน้าไหน
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
