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

# ชื่อไฟล์โลโก้ (ต้องตรงกับที่อัปโหลดใน GitHub)
LOGO_FILE = "school_logo.png"

def get_thailand_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    /* ปรับแต่งให้รูปโลโก้หน้าเว็บอยู่ตรงกลางสวยงาม */
    [data-testid="stImage"] { display: block; margin-left: auto; margin-right: auto; }
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

# --- 📄 3. ฟังก์ชันสร้าง PDF (เพิ่มโลโก้) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        font_path = "THSarabunNew.ttf"
        
        if not os.path.exists(font_path):
            return "MISSING_FONT"

        pdf.add_font('ThaiFont', '', font_path)
        epw = pdf.w - 2 * pdf.l_margin 
        
        # --- ส่วนที่ 1: หัวกระดาษ และ โลโก้ ---
        # ใส่โลโก้ที่มุมซ้ายบน (x=10mm, y=8mm, ความกว้าง=25mm)
        if os.path.exists(LOGO_FILE):
            pdf.image(LOGO_FILE, x=10, y=8, w=25)
        
        # ขยับเคอร์เซอร์ลงมาเล็กน้อยเพื่อให้ข้อความหัวกระดาษไม่ทับโลโก้
        pdf.set_y(15) 

        pdf.set_font('ThaiFont', '', 22)
        # ขยับข้อความไปทางขวาเล็กน้อยเพื่อให้สมดุลกับโลโก้
        pdf.cell(0, 12, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการ", ln=True, align='C')
        
        pdf.ln(5)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(8)

        # --- ส่วนที่ 2: ข้อมูลพื้นฐาน ---
        pdf.set_font('ThaiFont', '', 15)
        pdf.cell(epw/2, 10, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}", ln=0)
        pdf.cell(epw/2, 10, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", ln=1, align='R')
        
        pdf.multi_cell(epw, 10, txt=f"ประเภทเหตุการณ์: {row_data.get('Incident_Type', '-')}")
        pdf.multi_cell(epw, 10, txt=f"สถานที่เกิดเหตุ: {row_data.get('Location', '-')}")
        pdf.multi_cell(epw, 10, txt=f"ชื่อผู้แจ้งเหตุ: {row_data.get('Reporter', 'ไม่ประสงค์ออกนาม')}")
        
        pdf.ln(2)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(5)

        # --- ส่วนที่ 3: รายละเอียด ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(epw, 10, txt="รายละเอียดเหตุการณ์:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(epw, 8, txt=str(row_data.get('Details', '-')))
        pdf.ln(10)

        # --- ส่วนที่ 4: ผลการดำเนินการ ---
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(epw, 10, txt="ผลการดำเนินการของเจ้าหน้าที่:", ln=True)
        pdf.set_fill_color(248, 249, 250)
        pdf.set_font('ThaiFont', '', 14)
        
        status_info = f"สถานะปัจจุบัน: {row_data.get('Status', '-')}\nรายละเอียดการจัดการ: {row_data.get('Action_Details', '-')}"
        pdf.multi_cell(epw, 10, txt=status_info, border=1, fill=True)
        
        pdf.ln(25)

        # --- ส่วนที่ 5: ช่องลงนาม ---
        pdf.set_font('ThaiFont', '', 14)
        curr_y = pdf.get_y()
        if curr_y > 250: pdf.add_page(); curr_y = 20;

        pdf.set_xy(pdf.l_margin + 5, curr_y)
        pdf.cell(80, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(pdf.l_margin + 5)
        pdf.cell(80, 7, txt=f"( {row_data.get('Handled_By', '.................................')} )", ln=True, align='C')
        pdf.set_x(pdf.l_margin + 5)
        pdf.cell(80, 7, txt="เจ้าหน้าที่ผู้ดำเนินการ", ln=True, align='C')
        
        pdf.set_xy(pdf.w / 2 + 10, curr_y)
        pdf.cell(80, 7, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.set_x(pdf.w / 2 + 10)
        pdf.cell(80, 7, txt="(..........................................................)", ln=True, align='C')
        pdf.set_x(pdf.w / 2 + 10)
        pdf.cell(80, 7, txt="หัวหน้างานปกครอง/อาจารย์ที่ปรึกษา", ln=True, align='C')

        return pdf.output()
    except Exception as e:
        return f"PDF_GEN_ERROR: {str(e)}"

# --- 📋 4. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    
    # แสดงโลโก้ในหน้าเจ้าหน้าที่ (ถ้ามีไฟล์)
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([3, 2, 3]) # จัดกึ่งกลาง
        with c2:
            st.image(LOGO_FILE, use_container_width=True)
            
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

        tab1, tab2 = st.tabs(["🔎 รายการทั้งหมด", "🛠 บันทึกผลและพิมพ์เอกสาร"])

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
                        st.write(f"📝 **รายละเอียดแจ้งเหตุ:** {row['Details']}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                            new_st = st.selectbox("เปลี่ยนสถานะ", opts, index=opts.index(row['Status']) if row['Status'] in opts else 0)
                        with c_b:
                            act_txt = st.text_input("บันทึกรายละเอียดการจัดการ", value=row.get('Action_Details', ''))

                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Status'] = new_st
                            df.at[idx, 'Action_Details'] = act_txt
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.success("บันทึกสำเร็จ!")
                            st.rerun()
                        
                        pdf_data = create_pdf(row)
                        if isinstance(pdf_data, (bytes, bytearray)):
                            st.download_button("📥 พิมพ์ PDF ใบสรุปรายงาน", data=bytes(pdf_data), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
                        else:
                            st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {pdf_data}")
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมข้อมูลเท่านั้น")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    # แสดงโลโก้ในหน้าหลัก (ถ้ามีไฟล์)
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([3, 2, 3]) # ใช้ column เพื่อจัดกึ่งกลางและควบคุมขนาด
        with c2:
            # ปรับความกว้างตามต้องการ เช่น width=150
            st.image(LOGO_FILE, use_container_width=True) 

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>โรงเรียนโพนทองพัฒนาวิทยา</p>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขที่รับแจ้งของคุณคือ: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.container(border=True):
            with st.form("report_form"):
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
                        new_row = pd.DataFrame([{"Timestamp": now_th.strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep if rep else "ไม่ประสงค์ออกนาม", "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Action_Details": "", "Handled_By": "", "Report_ID": rid}])
                        conn.update(data=pd.concat([df_old, new_row], ignore_index=True))
                        st.session_state.submitted_id = rid
                        st.rerun()
                    else:
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")

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
