import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random
import os
from fpdf import FPDF

# --- 1. ตั้งค่าหน้าจอ (ต้องอยู่บนสุดเสมอ) ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

# CSS ตกแต่งและซ่อน UI ส่วนเกิน
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

# --- 🔑 2. ระบบจัดการสิทธิ์ ---
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

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'submitted_id' not in st.session_state:
    st.session_state.submitted_id = None

# --- 📄 3. ฟังก์ชันสร้าง PDF (แก้ไข Unicode Error) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "THSarabunNew.ttf" # ต้องมีไฟล์นี้ใน GitHub หน้าแรก
        
        if os.path.exists(font_path):
            pdf.add_font('ThaiFont', '', font_path)
            pdf.set_font('ThaiFont', '', 18)
            pdf.cell(pdf.epw, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font('ThaiFont', '', 14)
            
            lines = [
                f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}",
                f"วันเวลาแจ้ง: {row_data.get('Timestamp', '-')}",
                f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')}",
                f"สถานที่: {row_data.get('Location', '-')}",
                f"รายละเอียด: {row_data.get('Details', '-')}",
                f"สถานะล่าสุด: {row_data.get('Status', '-')}",
                f"บันทึกการดำเนินการ: {row_data.get('Action_Details', '-')}",
                f"เจ้าหน้าที่ผู้รับผิดชอบ: {row_data.get('Handled_By', '-')}"
            ]
            for line in lines:
                pdf.multi_cell(pdf.epw, 10, txt=line)
            return pdf.output()
        else:
            return "MISSING_FONT"
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 📋 4. หน้าจอเจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการเหตุการณ์ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col_h2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุ")
            return

        tab1, tab2 = st.tabs(["🔎 รายการแจ้งเหตุ", "🛠 บันทึกผลการจัดการ"])

        with tab1:
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                ids = df['Report_ID'].dropna().unique().tolist()
                selected_id = st.selectbox("เลือกเลขที่รับแจ้งเพื่อบันทึกงาน", ids)
                selection = df[df['Report_ID'] == selected_id]
                
                if not selection.empty:
                    idx = selection.index[0]
                    row = selection.iloc[0]
                    with st.container(border=True):
                        st.write(f"📝 **รายละเอียด:** {row['Details']}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            status_opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                            curr_st = row['Status'] if row['Status'] in status_opts else "รอดำเนินการ"
                            new_st = st.selectbox("เปลี่ยนสถานะ", status_opts, index=status_opts.index(curr_st))
                        with c_b:
                            act_txt = st.text_input("รายละเอียดการจัดการ", value=row.get('Action_Details', ''))

                        # แก้ไข NameError โดยวางปุ่มไว้ใน Logic ของการเลือกข้อมูล
                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Status'] = new_st
                            df.at[idx, 'Action_Details'] = act_txt
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("✅ บันทึกและอัปเดตข้อมูลสำเร็จ!")
                            st.rerun()
                        
                        # ระบบ PDF (แบบ Bytes ปลอดภัยจาก Unicode Error)
                        pdf_result = create_pdf(row)
                        if isinstance(pdf_result, (bytes, bytearray)):
                            st.download_button("📥 พิมพ์ PDF สรุปงาน", data=bytes(pdf_result), file_name=f"Report_{selected_id}.pdf", mime="application/pdf", use_container_width=True)
                        elif pdf_result == "MISSING_FONT":
                            st.error("หาไฟล์ THSarabunNew.ttf ไม่เจอใน GitHub")
                        else:
                            st.error(pdf_result)
            else:
                st.warning("🔒 คุณมีสิทธิ์เข้าชมเท่านั้น ไม่สามารถบันทึกข้อมูลได้")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขที่รับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("ส่งเรื่องใหม่", use_container_width=True):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.container(border=True):
            with st.form("report"):
                col1, col2 = st.columns(2)
                with col1:
                    rep = st.text_input("ชื่อผู้แจ้ง")
                    typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
                with col2:
                    loc = st.text_input("สถานที่เกิดเหตุ *")
                det = st.text_area("รายละเอียดเหตุการณ์ *")
                if st.form_submit_button("📤 ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
                    if loc and det:
                        rid = f"POL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                        df_old = conn.read(ttl=0)
                        new_r = pd.DataFrame([{"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Action_Details": "", "Handled_By": "", "Report_ID": rid}])
                        conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                        st.session_state.submitted_id = rid
                        st.rerun()
                    else:
                        st.error("กรุณากรอกข้อมูลสถานที่และรายละเอียด")

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("ใส่รหัสผ่านเพื่อเข้าจัดการ", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# --- 🚀 6. ควบคุมการรันแอป ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
