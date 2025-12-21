import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. การตั้งค่าหน้าจอและสไตล์ (UI Decoration) ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

# Custom CSS เพื่อความสวยงาม
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebar"] {display: none;}
    
    /* ปรับแต่งกล่อง Metric ให้ดูเด่นขึ้น */
    [data-testid="stMetricValue"] { font-size: 28px; color: #1E3A8A; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; 
        border-radius: 10px 10px 0px 0px; 
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    
    /* ปรับแต่งส่วนหัวของหน้า */
    .main-header { font-size: 32px; font-weight: bold; color: #1E3A8A; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ระบบจัดการสิทธิ์ (OFFICER_ACCOUNTS) ---
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
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
        st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ (สวยงามสไตล์ใหม่) ---
def officer_dashboard():
    user = st.session_state.current_user
    
    # Header ส่วนบน
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการสารวัตรนักเรียน</div>", unsafe_allow_html=True)
        st.write(f"สวัสดีครับคุณ **{user['name']}** (สิทธิ์: {user['role']})")
    with col_head2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read()
        if df.empty:
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุ")
            return

        # --- 📊 ส่วนสรุปยอด (Metrics) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เหตุการณ์ทั้งหมด", len(df))
        m2.metric("🔴 รอดำเนินการ", len(df[df['Status'] == 'รอดำเนินการ']))
        m3.metric("🟡 กำลังจัดการ", len(df[df['Status'] == 'กำลังจัดการ']))
        m4.metric("🟢 จัดการแล้ว", len(df[df['Status'] == 'จัดการแล้ว']))

        st.markdown("---")

        # --- 📑 ส่วนแถบเมนูแยกเป็นสัดส่วน (Tabs) ---
        tab1, tab2, tab3 = st.tabs(["🔎 รายการแจ้งเหตุ", "🛠 จัดการสถานะ", "🗑 ลบข้อมูล"])

        with tab1:
            st.subheader("ฐานข้อมูลเหตุการณ์")
            # เพิ่มฟิลเตอร์ง่ายๆ
            status_filter = st.multiselect("กรองตามสถานะ", options=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], default=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว"])
            filtered_df = df[df['Status'].isin(status_filter)]
            st.dataframe(filtered_df, use_container_width=True, height=400)

        with tab2:
            if user['role'] == 'admin':
                st.subheader("แก้ไขสถานะเหตุการณ์")
                with st.container(border=True):
                    edit_row = st.selectbox("เลือกรายการที่ต้องการแก้ไข (ดูจากลำดับในตารางด้านบน)", df.index)
                    st.write(f"**เหตุการณ์:** {df.at[edit_row, 'Incident_Type']} | **สถานที่:** {df.at[edit_row, 'Location']}")
                    new_status = st.select_slider("ปรับเปลี่ยนสถานะ", options=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"])
                    if st.button("ยืนยันการเปลี่ยนสถานะ", type="primary"):
                        df.at[edit_row, 'Status'] = new_status
                        update_db(df)
            else:
                st.warning("🔒 เฉพาะเจ้าหน้าที่ระดับผู้บริหารที่สามารถแก้ไขสถานะได้")

        with tab3:
            if user['role'] == 'admin':
                st.subheader("ลบข้อมูลออกจากระบบ")
                with st.container(border=True):
                    del_row = st.number_input("ใส่หมายเลขลำดับแถวที่ต้องการลบ", min_value=0, max_value=len(df)-1, step=1)
                    st.error(f"⚠️ คำเตือน: คุณกำลังจะลบข้อมูลของ: {df.at[del_row, 'Incident_Type']} ที่ {df.at[del_row, 'Location']}")
                    if st.button("🗑 ยืนยันการลบถาวร", type="secondary"):
                        df = df.drop(df.index[del_row])
                        update_db(df)
            else:
                st.warning("🔒 เฉพาะแอดมินสูงสุดที่สามารถลบข้อมูลได้")

    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลได้: {e}")

# --- 📝 4. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    # เพิ่มภาพหรือโลโก้โรงเรียนตรงนี้ได้
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📢 แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>โรงเรียนโพนทองพัฒนาวิทยา</p>", unsafe_allow_html=True)
    
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
        st.success("✅ ข้อมูลส่งถึงสารวัตรนักเรียนเรียบร้อยแล้ว")
        st.balloons()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pwd = st.text_input("รหัสผ่านประจำตัว", type="password")
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            if pwd in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pwd]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# --- 🚀 5. ส่วนควบคุมหน้าการแสดงผล ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
