import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random  # <--- สำคัญมาก ห้ามลืมตัวนี้ครับ

# --- 1. ตั้งค่าหน้าจอ (ต้องอยู่บรรทัดแรกสุดของ Streamlit เสมอ) ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

# CSS เพื่อซ่อนส่วนที่ไม่จำเป็นและตกแต่งหน้าจอ
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { 
        background-color: #f0f9ff; 
        border: 2px solid #1E3A8A; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
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

if 'submitted_id' not in st.session_state:
    st.session_state.submitted_id = None

# ฟังก์ชันอัปเดตข้อมูล
def update_db(df):
    try:
        conn.update(data=df)
        st.success("✅ บันทึกข้อมูลสำเร็จ")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

# --- 📋 3. หน้าจอเจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการเหตุการณ์ ({user['name']})</div>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        
        if df is None or df.empty:
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุในระบบ")
            return

        # ตรวจสอบว่าคอลัมน์สำคัญมีครบไหม ถ้าไม่มีให้สร้างหลอกไว้ก่อน
        for col in ['Status', 'Action_Details', 'Handled_By', 'Report_ID']:
            if col not in df.columns:
                df[col] = ""

        # ส่วนแสดงสรุปยอด
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ทั้งหมด", len(df))
        m2.metric("🔴 รอดำเนินการ", len(df[df['Status'] == 'รอดำเนินการ']))
        m3.metric("🟡 กำลังจัดการ", len(df[df['Status'] == 'กำลังจัดการ']))
        m4.metric("🟢 จัดการแล้ว", len(df[df['Status'] == 'จัดการแล้ว']))

        tab1, tab2 = st.tabs(["🔎 ตารางจัดการเหตุ", "🛠 อัปเดตการดำเนินงาน"])

        with tab1:
            st.subheader("ฐานข้อมูลล่าสุด")
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                with st.container(border=True):
                    report_list = df['Report_ID'].dropna().unique().tolist()
                    if report_list:
                        selected_id = st.selectbox("เลือกเลขที่รับแจ้ง", report_list)
                        selection = df[df['Report_ID'] == selected_id]
                        
                        if not selection.empty:
                            row_idx = selection.index[0]
                            row_data = selection.iloc[0]

                            st.write(f"📌 **เหตุการณ์:** {row_data['Incident_Type']} | **สถานที่:** {row_data['Location']}")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                                curr_status = row_data['Status'] if row_data['Status'] in opts else "รอดำเนินการ"
                                new_status = st.selectbox("สถานะ", opts, index=opts.index(curr_status))
                            with col_b:
                                st.text_input("ผู้รับผิดชอบ", value=user['name'], disabled=True)
                            
                            action_detail = st.text_area("บันทึกการจัดการ", value=row_data['Action_Details'] if pd.notna(row_data['Action_Details']) else "")

                            if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                                df.at[row_idx, 'Status'] = new_status
                                df.at[row_idx, 'Action_Details'] = action_detail
                                df.at[row_idx, 'Handled_By'] = user['name']
                                update_db(df)
                    else:
                        st.write("ยังไม่มีเลขรับแจ้งที่สามารถจัดการได้")
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมเท่านั้น")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 📝 4. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>โรงเรียนโพนทองพัฒนาวิทยา</p>", unsafe_allow_html=True)

    if st.session_state.submitted_id:
        st.markdown(f"""
            <div class='report-id-box'>
                <h2 style='color: #15803d;'>✅ แจ้งเหตุสำเร็จ</h2>
                <p>เลขที่รับแจ้งของคุณคือ</p>
                <h1 style='color: #1E3A8A;'>{st.session_state.submitted_id}</h1>
                <p>ถ่ายภาพหน้าจอนี้เก็บไว้เพื่อติดตามผล</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("แจ้งเหตุใหม่", use_container_width=True):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.container(border=True):
            with st.form(key="report"):
                c1, c2 = st.columns(2)
                with c1:
                    rep = st.text_input("ชื่อผู้แจ้ง (ถ้ามี)")
                    typ = st.selectbox("ประเภท", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
                with c2:
                    loc = st.text_input("สถานที่ *")
                det = st.text_area("รายละเอียด *")
                submit = st.form_submit_button("📤 ส่งข้อมูล", use_container_width=True)

        if submit and loc and det:
            rid = f"POL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            try:
                df_old = conn.read(ttl=0)
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Reporter": rep if rep else "ไม่ประสงค์ออกนาม",
                    "Incident_Type": typ,
                    "Location": loc,
                    "Details": det,
                    "Status": "รอดำเนินการ",
                    "Action_Details": "",
                    "Handled_By": "",
                    "Report_ID": rid
                }])
                updated = pd.concat([df_old, new_row], ignore_index=True)
                conn.update(data=updated)
                st.session_state.submitted_id = rid
                st.rerun()
            except Exception as e:
                st.error(f"การส่งข้อมูลล้มเหลว: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 เจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()
            else:
                st.error("รหัสผิด")

# --- 🚀 5. ส่วนควบคุมหลัก ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
