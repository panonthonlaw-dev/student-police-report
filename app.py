import streamlit as st  # บรรทัดนี้ต้องอยู่บนสุดเสมอ
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random
import requests
import os
from fpdf import FPDF

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

# CSS ตกแต่ง
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    </style>
""", unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ข้อมูลเจ้าหน้าที่ ---
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

# --- 📄 3. ระบบ PDF และฟอนต์ไทย (โหลดอัตโนมัติ) ---
@st.cache_data
def load_font_file():
    # โหลดฟอนต์ภาษาไทยจาก Google Fonts (Noto Sans Thai)
    url = "https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai-Regular.ttf"
    font_path = "ThaiFont.ttf"
    if not os.path.exists(font_path):
        try:
            r = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except:
            return None
    return font_path

def create_pdf(row_data):
    pdf = FPDF()
    pdf.add_page()
    
    f_path = load_font_file()
    if f_path:
        pdf.add_font('ThaiFont', '', f_path)
        pdf.set_font('ThaiFont', '', 16)
    else:
        pdf.set_font('Arial', '', 12)

    # เนื้อหา PDF
    pdf.cell(pdf.epw, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
    pdf.ln(10)
    
    # ข้อมูลรายละเอียด (รองรับไทย)
    content = [
        f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}",
        f"วันเวลาแจ้ง: {row_data.get('Timestamp', '-')}",
        f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')}",
        f"สถานที่: {row_data.get('Location', '-')}",
        f"รายละเอียด: {row_data.get('Details', '-')}",
        f"สถานะล่าสุด: {row_data.get('Status', '-')}",
        f"การดำเนินการ: {row_data.get('Action_Details', '-')}",
        f"ผู้รับผิดชอบ: {row_data.get('Handled_By', '-')}"
    ]
    
    for item in content:
        pdf.multi_cell(pdf.epw, 10, txt=item)
    
    return pdf.output()

# --- 📋 4. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col2:
        if st.button("🔴 ออกจากระบบ"):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุ")
            return

        tab1, tab2 = st.tabs(["🔎 ตารางจัดการ", "🛠 ดำเนินการ/พิมพ์ PDF"])
        
        with tab1:
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                ids = df['Report_ID'].dropna().unique().tolist()
                sid = st.selectbox("เลือกเลขที่รับแจ้ง", ids)
                sel = df[df['Report_ID'] == sid]
                
                if not sel.empty:
                    idx = sel.index[0]
                    row = sel.iloc[0]
                    with st.container(border=True):
                        st.write(f"📌 **รายละเอียด:** {row['Details']}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            new_st = st.selectbox("เปลี่ยนสถานะ", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], 
                                               index=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"].index(row['Status']) if row['Status'] in ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"] else 0)
                        with c_b:
                            act_txt = st.text_input("บันทึกการจัดการ", value=row.get('Action_Details', ''))

                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Status'] = new_st
                            df.at[idx, 'Action_Details'] = act_txt
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("บันทึกสำเร็จ!")
                            st.rerun()
                        
                        # สร้าง PDF
                        pdf_bytes = create_pdf(row)
                        st.download_button("📥 พิมพ์เอกสารสรุป (PDF)", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.warning("🔒 คุณมีสิทธิ์ Viewer (ดูได้อย่างเดียว)")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเหตุเพิ่ม"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.form("report"):
            rep = st.text_input("ชื่อผู้แจ้ง")
            typ = st.selectbox("ประเภท", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            loc = st.text_input("สถานที่ *")
            det = st.text_area("รายละเอียด *")
            if st.form_submit_button("📤 ส่งข้อมูล"):
                if loc and det:
                    rid = f"POL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    df_old = conn.read(ttl=0)
                    new_r = pd.DataFrame([{"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Action_Details": "", "Handled_By": "", "Report_ID": rid}])
                    conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                    st.session_state.submitted_id = rid
                    st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()

# --- 🚀 6. รันแอป ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
