import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import random
import os
from fpdf import FPDF

# --- 1. การตั้งค่าหน้าจอและเวลา ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"

def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ข้อมูลเจ้าหน้าที่ ---
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

# --- 📄 3. ฟังก์ชันสร้าง PDF (ปรับขอบกระดาษ + โลโก้เล็กลง + ข้อมูลสอบสวน) ---
def create_pdf(row_data):
    try:
        # ปรับ Margin ให้พอดี ไม่ตกขอบ (ซ้าย 15, บน 15, ขวา 15)
        pdf = FPDF(unit='mm', format='A4')
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        
        font_path = "THSarabunNew.ttf"
        if not os.path.exists(font_path): return "MISSING_FONT"
        pdf.add_font('ThaiFont', '', font_path)
        
        # --- หัวกระดาษ ---
        # ลดขนาดโลโก้ลงเหลือ 18mm
        if os.path.exists(LOGO_FILE):
            pdf.image(LOGO_FILE, x=15, y=12, w=18)
        
        pdf.set_y(15)
        pdf.set_font('ThaiFont', '', 20)
        pdf.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน", ln=True, align='C')
        
        pdf.ln(5)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(8)

        # --- ข้อมูลแจ้งเหตุ ---
        epw = pdf.w - 2 * pdf.l_margin 
        pdf.set_font('ThaiFont', '', 14)
        pdf.cell(epw/2, 8, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=0)
        pdf.cell(epw/2, 8, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", ln=1, align='R')
        pdf.cell(0, 8, txt=f"ประเภทเหตุการณ์: {row_data.get('Incident_Type', '-')}", ln=1)
        pdf.cell(0, 8, txt=f"สถานที่เกิดเหตุ: {row_data.get('Location', '-')}", ln=1)
        pdf.cell(0, 8, txt=f"ชื่อผู้แจ้งเหตุ: {row_data.get('Reporter', '-')}", ln=1)
        
        pdf.ln(2)
        pdf.set_font('ThaiFont', '', 15)
        pdf.cell(0, 8, txt="รายละเอียดเหตุการณ์เดิม:", ln=1)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(epw, 7, txt=str(row_data.get('Details', '-')))
        
        pdf.ln(5)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

        # --- ส่วนบันทึกการสอบสวน (ข้อมูลใหม่) ---
        pdf.set_font('ThaiFont', '', 15)
        pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวนและจัดการ:", ln=1)
        pdf.set_font('ThaiFont', '', 14)
        
        investigation_data = [
            f"ผู้เสียหาย: {row_data.get('Victim', '-')}",
            f"ผู้ถูกกล่าวหา: {row_data.get('Accused', '-')}",
            f"พยาน: {row_data.get('Witness', '-')}",
            f"ครูผู้สอบสวน: {row_data.get('Teacher_Investigator', '-')}",
            f"ตำรวจนักเรียนสอบสวน: {row_data.get('Student_Police_Investigator', '-')}",
            f"สถานะจัดการ: {row_data.get('Status', '-')}"
        ]
        
        for item in investigation_data:
            pdf.cell(0, 8, txt=item, ln=1)
        
        pdf.ln(2)
        pdf.multi_cell(epw, 8, txt=f"บันทึกคำให้การ/การดำเนินการ: {row_data.get('Statement', '-')}", border=1)

        # --- ส่วนลงนาม (ปรับไม่ให้ตกขอบล่าง) ---
        pdf.set_y(-50)
        curr_y = pdf.get_y()
        pdf.set_font('ThaiFont', '', 13)
        # ฝั่งซ้าย
        pdf.set_xy(15, curr_y)
        pdf.cell(85, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(15)
        pdf.cell(85, 7, txt=f"( {row_data.get('Handled_By', '.................................')} )", ln=True, align='C')
        pdf.set_x(15)
        pdf.cell(85, 7, txt="เจ้าหน้าที่ผู้ดำเนินการ/บันทึก", ln=True, align='C')
        
        # ฝั่งขวา
        pdf.set_xy(110, curr_y)
        pdf.cell(85, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(110)
        pdf.cell(85, 7, txt="(..........................................................)", ln=True, align='C')
        pdf.set_x(110)
        pdf.cell(85, 7, txt="หัวหน้างานปกครอง/อาจารย์ที่ปรึกษา", ln=True, align='C')

        return pdf.output()
    except Exception as e:
        return f"PDF_ERROR: {str(e)}"

# --- 📋 4. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    
    # โลโก้หน้าเจ้าหน้าที่ให้เล็กลง (3:1:3)
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]) 
        with c2: st.image(LOGO_FILE, width=80)
            
    col1, col2 = st.columns([4, 1])
    with col1: st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            st.info("ไม่มีข้อมูล")
            return

        tab1, tab2 = st.tabs(["🔎 รายการทั้งหมด", "🛠 สอบสวนและบันทึกผล"])

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
                        st.subheader(f"🔢 เลขที่รับแจ้ง: {sid}")
                        st.write(f"🚩 **เหตุการณ์:** {row['Incident_Type']} | **สถานที่:** {row['Location']}")
                        st.write(f"📝 **รายละเอียดเดิม:** {row['Details']}")
                        st.markdown("---")
                        
                        st.write("📋 **บันทึกการสอบสวนเพิ่มเติม**")
                        c1, c2 = st.columns(2)
                        with c1:
                            v_victim = st.text_input("ผู้เสียหาย", value=row.get('Victim', ''))
                            v_accused = st.text_input("ผู้ถูกกล่าวหา", value=row.get('Accused', ''))
                            v_witness = st.text_input("พยาน", value=row.get('Witness', ''))
                        with c2:
                            v_teacher = st.text_input("ครูผู้สอบสวน", value=row.get('Teacher_Investigator', ''))
                            v_student = st.text_input("ตำรวจนักเรียนสอบสวน", value=row.get('Student_Police_Investigator', ''))
                            v_status = st.selectbox("สถานะจัดการ", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], index=0)
                        
                        v_statement = st.text_area("บันทึกคำให้การ/รายละเอียดการดำเนินการ", value=row.get('Statement', ''))

                        if st.button("💾 บันทึกการสอบสวน", type="primary", use_container_width=True):
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
                        
                        pdf_data = create_pdf(df.loc[idx])
                        if isinstance(pdf_data, (bytes, bytearray)):
                            st.download_button("📥 พิมพ์ PDF ใบสรุปผลสอบสวน", data=bytes(pdf_data), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.warning("🔒 Viewer Only")
    except Exception as e: st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]) 
        with c2: st.image(LOGO_FILE, width=100) # โลโก้หน้าแรกเล็กลง

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>โรงเรียนโพนทองพัฒนาวิทยา</p>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"):
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
                        now_th = get_thailand_time()
                        rid = f"POL-{now_th.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                        df_old = conn.read(ttl=0)
                        # สร้างแถวใหม่พร้อมคอลัมน์สอบสวนที่ว่างไว้
                        new_r = pd.DataFrame([{"Timestamp": now_th.strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Victim": "", "Accused": "", "Witness": "", "Teacher_Investigator": "", "Student_Police_Investigator": "", "Statement": "", "Handled_By": ""}])
                        conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                        st.session_state.submitted_id = rid
                        st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
