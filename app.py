import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ระบบจัดการสิทธิ์ ---
OFFICER_ACCOUNTS = {
    "Patwit1510": {"name": "แอดมินสูงสุด", "role": "admin"},
    "Pencharee001": {"name": "ครูเพ็ญชรีย์ (ปกครอง)", "role": "admin"},
    "Chaiya001": {"name": "ครูไชยา (ปกครอง)", "role": "admin"},
    "Jak001": {"name": "ยามจักร (รปภ.)", "role": "admin"},
    "User01": {"name": "ผู้กำกับ (ตำรวจนักเรียน)", "role": "admin"},
    "User02": {"name": "รองผู้กำกับจราจร (ตำรวจนักเรียน)", "role": "admin"},
    "User03": {"name": "ครูเวร (ตรวจการณ์)", "role": "viewer"},
    "User04": {"name": "ตำรวจนักเรียน", "role": "viewer"}
}

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def update_db(df):
    try:
        conn.update(data=df)
        st.success("✅ บันทึกข้อมูลและอัปเดตสถานะสำเร็จ!")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='main-header'>🏢 จัดการเหตุการณ์: คุณ {user['name']}</div>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        # ใช้ ttl=0 เพื่อให้ดึงข้อมูลใหม่ล่าสุดเสมอ
        df = conn.read(ttl=0)
        
        # แสดงสรุปยอด (Metrics)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ทั้งหมด", len(df))
        m2.metric("🔴 รอ", len(df[df['Status'] == 'รอดำเนินการ']))
        m3.metric("🟡 กำลังทำ", len(df[df['Status'] == 'กำลังจัดการ']))
        m4.metric("🟢 สำเร็จ", len(df[df['Status'] == 'จัดการแล้ว']))

        tab1, tab2 = st.tabs(["🔎 รายการทั้งหมด", "🛠 บันทึกการจัดการเหตุ"])

        with tab1:
            st.subheader("ตารางข้อมูลล่าสุด")
            st.dataframe(df, use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                st.subheader("อัปเดตการทำงาน")
                with st.container(border=True):
                    # เลือกแถวที่ต้องการจัดการ
                    row_idx = st.selectbox("เลือกรายการที่จัดการแล้ว (ดูตามลำดับแถว)", df.index)
                    
                    st.info(f"📌 **เหตุการณ์:** {df.at[row_idx, 'Incident_Type']} | **สถานที่:** {df.at[row_idx, 'Location']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_status = st.selectbox("เปลี่ยนสถานะ", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], 
                                                index=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"].index(df.at[row_idx, 'Status']))
                    with col_b:
                        st.write(f"✍️ **ผู้บันทึก:** {user['name']}")
                    
                    # ช่องกรอกรายละเอียดการจัดการ
                    action_detail = st.text_area("รายละเอียดการดำเนินการ (เช่น เรียกมาตักเตือน, แจ้งครูที่ปรึกษาแล้ว)", 
                                               value=df.at[row_idx, 'Action_Details'] if 'Action_Details' in df.columns else "")

                    if st.button("💾 บันทึกการดำเนินการ", type="primary", use_container_width=True):
                        df.at[row_idx, 'Status'] = new_status
                        df.at[row_idx, 'Action_Details'] = action_detail
                        df.at[row_idx, 'Handled_By'] = user['name']
                        update_db(df)
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมเท่านั้น ไม่สามารถบันทึกรายละเอียดการจัดการได้")

    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลได้: {e}")

# --- 📝 4. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        with st.form(key="report_form"):
            col1, col2 = st.columns(2)
            with col1:
                reporter = st.text_input("ชื่อผู้แจ้ง (ไม่ระบุก็ได้)")
                i_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            with col2:
                loc = st.text_input("สถานที่เกิดเหตุ *")
            det = st.text_area("รายละเอียดเหตุการณ์ *")
            submit = st.form_submit_button("📤 ส่งข้อมูล", use_container_width=True)

    if submit and loc and det:
        # ดึงข้อมูลล่าสุดมาก่อน (ttl=0)
        df_old = conn.read(ttl=0)
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
            "Incident_Type": i_type,
            "Location": loc,
            "Details": det,
            "Status": "รอดำเนินการ",
            "Action_Details": "",
            "Handled_By": ""
        }])
        updated_df = pd.concat([df_old, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("✅ แจ้งเหตุสำเร็จ!")
        st.balloons()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 เข้าสู่ระบบเจ้าหน้าที่"):
        pwd = st.text_input("รหัสผ่านประจำตัว", type="password")
        if st.button("Login", use_container_width=True):
            if pwd in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pwd]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
