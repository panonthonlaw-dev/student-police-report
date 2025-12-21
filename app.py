import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random

# --- 1. ตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

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

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ระบบจัดการสิทธิ์ (เหมือนเดิม) ---
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
        st.success("✅ บันทึกข้อมูลเรียบร้อย")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ ---
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
        
        # สรุปยอด
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ทั้งหมด", len(df))
        m2.metric("🔴 รอดำเนินการ", len(df[df['Status'] == 'รอดำเนินการ']))
        m3.metric("🟡 กำลังจัดการ", len(df[df['Status'] == 'กำลังจัดการ']))
        m4.metric("🟢 จัดการแล้ว", len(df[df['Status'] == 'จัดการแล้ว']))

        tab1, tab2 = st.tabs(["🔎 ตารางจัดการเหตุ (ตามเลขรับแจ้ง)", "🛠 อัปเดตการดำเนินงาน"])

        with tab1:
            st.subheader("ฐานข้อมูลเหตุการณ์ (เรียงจากล่าสุด)")
            # แสดงคอลัมน์เลขรับแจ้งให้ชัดเจน
            st.dataframe(df.iloc[::-1], use_container_width=True) # แสดงย้อนกลับเอาอันใหม่ขึ้นบน

        with tab2:
            if user['role'] == 'admin':
                with st.container(border=True):
                    # เลือกตามเลขที่รับแจ้งแทนการลำดับแถวเพื่อให้แม่นยำขึ้น
                    report_list = df['Report_ID'].tolist()
                    selected_id = st.selectbox("เลือกเลขที่รับแจ้งที่ต้องการจัดการ", report_list)
                    
                    # ดึงข้อมูลแถวที่เลือก
                    row_data = df[df['Report_ID'] == selected_id].iloc[0]
                    row_idx = df[df['Report_ID'] == selected_id].index[0]

                    st.markdown(f"**เหตุการณ์:** {row_data['Incident_Type']} | **สถานที่:** {row_data['Location']}")
                    st.write(f"**รายละเอียด:** {row_data['Details']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_status = st.selectbox("สถานะการดำเนินงาน", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], 
                                                index=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"].index(row_data['Status']))
                    with col_b:
                        action_by = st.text_input("เจ้าหน้าที่ผู้รับผิดชอบ", value=user['name'], disabled=True)
                    
                    action_detail = st.text_area("บันทึกรายละเอียดการจัดการ", value=row_data['Action_Details'] if pd.notna(row_data['Action_Details']) else "")

                    if st.button("💾 บันทึกการดำเนินงาน", type="primary", use_container_width=True):
                        df.at[row_idx, 'Status'] = new_status
                        df.at[row_idx, 'Action_Details'] = action_detail
                        df.at[row_idx, 'Handled_By'] = user['name']
                        update_db(df)
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมเท่านั้น")

    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 4. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if 'submitted_id' not in st.session_state:
        st.session_state.submitted_id = None

    if st.session_state.submitted_id:
        # แสดงเลขรับแจ้งหลังส่งสำเร็จ
        st.markdown(f"""
            <div class='report-id-box'>
                <h2 style='color: #15803d;'>✅ ส่งแจ้งเหตุสำเร็จ!</h2>
                <p>เลขที่รับแจ้งของคุณคือ</p>
                <h1 style='color: #1E3A8A;'>{st.session_state.submitted_id}</h1>
                <p>⚠️ กรุณาจดบันทึก หรือถ่ายภาพหน้าจอนี้ไว้เพื่อใช้ติดตามสถานะ</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("แจ้งเหตุเพิ่ม/กลับหน้าหลัก", use_container_width=True):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.container(border=True):
            with st.form(key="report_form"):
                col1, col2 = st.columns(2)
                with col1:
                    reporter = st.text_input("ชื่อผู้แจ้ง (ไม่ระบุก็ได้)")
                    i_type = st.selectbox("ประเภทเหตุการณ์", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
                with col2:
                    loc = st.text_input("สถานที่เกิดเหตุ *")
                det = st.text_area("รายละเอียดเหตุการณ์ *")
                submit = st.form_submit_button("📤 ส่งข้อมูลแจ้งเหตุ", use_container_width=True)

        if submit and loc and det:
            # 1. สร้างเลขที่รับแจ้ง (Format: POL-YYYYMMDD-Random)
            now = datetime.now()
            report_id = f"POL-{now.strftime('%Y%md')}-{random.randint(1000, 9999)}"
            
            df_old = conn.read(ttl=0)
            new_row = pd.DataFrame([{
                "Timestamp": now.strftime("%d/%m/%Y %H:%M:%S"),
                "Reporter": reporter if reporter else "ไม่ประสงค์ออกนาม",
                "Incident_Type": i_type,
                "Location": loc,
                "Details": det,
                "Status": "รอดำเนินการ",
                "Action_Details": "",
                "Handled_By": "",
                "Report_ID": report_id
            }])
            updated_df = pd.concat([df_old, new_row], ignore_index=True)
            conn.update(data=updated_df)
            
            # บันทึก ID ลง session เพื่อแสดงให้คนแจ้งดู
            st.session_state.submitted_id = report_id
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pwd = st.text_input("รหัสผ่านประจำตัว", type="password")
        if st.button("Login"):
            if pwd in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pwd]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
