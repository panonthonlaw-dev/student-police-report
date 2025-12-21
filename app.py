import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz # เพิ่มสำหรับการจัดการเวลาประเทศไทย
import random
import os
from fpdf import FPDF

# --- 1. การตั้งค่าระบบเวลาประเทศไทย ---
def get_now_th():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

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

# --- 📄 3. ฟังก์ชันสร้าง PDF (ปรับปรุง Layout และระยะบรรทัด) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "THSarabunNew.ttf"
        
        if not os.path.exists(font_path):
            return "MISSING_FONT"

        pdf.add_font('ThaiFont', '', font_path)
        
        # --- หัวกระดาษ ---
        pdf.set_font('ThaiFont', '', 22)
        pdf.cell(0, 12, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการ", ln=True, align='C')
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        # --- ข้อมูลทั่วไป ---
        pdf.set_font('ThaiFont', '', 15)
        # เลขที่รับแจ้ง และ วันที่ (แยกซ้ายขวา)
        y_pos = pdf.get_y()
        pdf.set_xy(10, y_pos)
        pdf.cell(95, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}")
        pdf.set_xy(105, y_pos)
        pdf.cell(95, 10, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", align='R')
        pdf.ln(10)

        pdf.multi_cell(0, 10, txt=f"ประเภทเหตุการณ์: {row_data.get('Incident_Type', '-')}")
        pdf.multi_cell(0, 10, txt=f"สถานที่เกิดเหตุ: {row_data.get('Location', '-')}")
        pdf.multi_cell(0, 10, txt=f"ชื่อผู้แจ้งเหตุ: {row_data.get('Reporter', 'ไม่ประสงค์ออกนาม')}")
        
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # --- รายละเอียดเหตุการณ์ (ใช้ multi_cell เพื่อป้องกันการทับกัน) ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="รายละเอียดเหตุการณ์:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(0, 8, txt=str(row_data.get('Details', '-')))
        pdf.ln(10)

        # --- ผลการดำเนินงาน ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ผลการดำเนินการของเจ้าหน้าที่:", ln=True)
        
        # กล่องข้อมูลสถานะ
        pdf.set_fill_color(248, 249, 250)
        pdf.set_font('ThaiFont', '', 14)
        status_txt = f"สถานะปัจจุบัน: {row_data.get('Status', '-')}\nรายละเอียดการจัดการ: {row_data.get('Action_Details', '-')}"
        # คำนวณความสูงอัตโนมัติจากเนื้อหา
        pdf.multi_cell(0, 10, txt=status_txt, border=1, fill=True)
        
        pdf.ln(25) # เว้นระยะสำหรับเซ็นชื่อ

        # --- ส่วนลงนาม (จัดตำแหน่งใหม่ให้สมดุล) ---
        curr_y = pdf.get_y()
        if curr_y > 240: # ถ้าใกล้หมดหน้าให้ขึ้นหน้าใหม่
            pdf.add_page()
            curr_y = 20
            
        pdf.set_font('ThaiFont', '', 14)
        # ฝั่งซ้าย
        pdf.set_xy(15, curr_y)
        pdf.cell(80, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(15)
        pdf.cell(80, 7, txt=f"( {row_data.get('Handled_By', '.................................')} )", ln=True, align='C')
        pdf.set_x(15)
        pdf.cell(80, 7, txt="เจ้าหน้าที่ผู้ดำเนินการ", ln=True, align='C')
        
        # ฝั่งขวา
        pdf.set_xy(115, curr_y)
        pdf.cell(80, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(115)
        pdf.cell(80, 7, txt="(..........................................................)", ln=True, align='C')
        pdf.set_x(115)
        pdf.cell(80, 7, txt="อาจารย์ที่ปรึกษา/หัวหน้างานปกครอง", ln=True, align='C')

        return pdf.output()
    except Exception as e:
        return f"ERROR: {str(e)}"

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
            st.info("ยังไม่มีข้อมูลการแจ้งเหตุ")
            return

        tab1, tab2 = st.tabs(["🔎 รายการแจ้งเหตุ", "🛠 บันทึกผลและพิมพ์เอกสาร"])

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
                        st.write(f"📝 **รายละเอียด:** {row['Details']}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                            new_st = st.selectbox("เปลี่ยนสถานะ", opts, index=opts.index(row['Status']) if row['Status'] in opts else 0)
                        with c_b:
                            act_txt = st.text_input("บันทึกการจัดการ", value=row.get('Action_Details', ''))

                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Status'] = new_st
                            df.at[idx, 'Action_Details'] = act_txt
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("บันทึกสำเร็จ!")
                            st.rerun()
                        
                        pdf_res = create_pdf(row)
                        if isinstance(pdf_res, (bytes, bytearray)):
                            st.download_button("📥 พิมพ์ PDF ใบสรุปงาน", data=bytes(pdf_res), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
                        else:
                            st.error(f"สร้าง PDF ไม่สำเร็จ: {pdf_res}")
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมเท่านั้น")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขที่รับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("ส่งเรื่องใหม่"):
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
                        # สร้าง ID และบันทึกเวลาประเทศไทย
                        now_th = get_now_th()
                        rid = f"POL-{now_th.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                        df_old = conn.read(ttl=0)
                        new_r = pd.DataFrame([{"Timestamp": now_th.strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Action_Details": "", "Handled_By": "", "Report_ID": rid}])
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

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
