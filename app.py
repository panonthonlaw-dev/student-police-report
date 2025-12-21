import streamlit as st
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

# --- 📄 3. ระบบ PDF (ปรับปรุงใหม่เพื่อแก้ Error พื้นที่) ---
@st.cache_data
def download_font():
    # ใช้ฟอนต์สารบรรณจากแหล่งที่เสถียร
    url = "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Medium.ttf"
    target_path = "ThaiFont.ttf"
    if not os.path.exists(target_path):
        r = requests.get(url)
        with open(target_path, "wb") as f:
            f.write(r.content)
    return target_path

def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_p = download_font()
        
        pdf.add_font('ThaiFont', '', font_p)
        pdf.set_font('ThaiFont', '', 18)
        
        # ส่วนหัว
        pdf.cell(pdf.epw, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font('ThaiFont', '', 14)
        # ใช้ pdf.epw (Effective Page Width) เพื่อป้องกัน Error พื้นที่ไม่พอ
        pdf.cell(pdf.epw, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"วันเวลาแจ้ง: {row_data.get('Timestamp', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')}", ln=True)
        pdf.cell(pdf.epw, 10, txt=f"สถานที่: {row_data.get('Location', '-')}", ln=True)
        
        pdf.ln(5)
        pdf.multi_cell(pdf.epw, 10, txt=f"รายละเอียดเหตุ: {row_data.get('Details', '-')}")
        
        pdf.ln(5)
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(pdf.epw, 10, txt=f"สถานะการจัดการ: {row_data.get('Status', '-')}", ln=True)
        
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(pdf.epw, 10, txt=f"บันทึกการดำเนินการ: {row_data.get('Action_Details', '-')}")
        pdf.cell(pdf.epw, 10, txt=f"เจ้าหน้าที่ผู้รับผิดชอบ: {row_data.get('Handled_By', '-')}", ln=True)
        
        return pdf.output()
    except Exception as e:
        return f"PDF Error: {str(e)}".encode('utf-8')

# --- 📋 4. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            st.info("ยังไม่มีข้อมูล")
            return

        tab1, tab2 = st.tabs(["🔎 ตารางจัดการ", "🛠 ดำเนินการ/พิมพ์ PDF"])

        with tab1:
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                report_ids = df['Report_ID'].dropna().unique().tolist()
                sid = st.selectbox("เลือกเลขที่รับแจ้ง", report_ids)
                sel = df[df['Report_ID'] == sid]
                
                if not sel.empty:
                    idx = sel.index[0]
                    row = sel.iloc[0]
                    
                    with st.container(border=True):
                        st.write(f"📌 **รายละเอียดเดิม:** {row['Details']}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            st_opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                            curr_st = row['Status'] if row['Status'] in st_opts else "รอดำเนินการ"
                            new_st = st.selectbox("เปลี่ยนสถานะ", st_opts, index=st_opts.index(curr_st))
                        with c_b:
                            act_detail = st.text_input("บันทึกการจัดการ", value=row.get('Action_Details', ''))

                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Status'] = new_st
                            df.at[idx, 'Action_Details'] = act_detail
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("บันทึกสำเร็จ!")
                            st.rerun()
                        
                        # สร้าง PDF
                        pdf_bytes = create_pdf(row)
                        st.download_button("📥 พิมพ์ PDF สรุปงาน", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.warning("🔒 สิทธิ์ของคุณคือ Viewer")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งแจ้งเหตุสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
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
                else:
                    st.error("กรุณากรอกข้อมูลให้ครบ")

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# --- 🚀 6. รันแอป ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
