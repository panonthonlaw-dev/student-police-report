import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random
import os
import base64
from fpdf import FPDF
from PIL import Image
import io

# --- 1. การตั้งค่าหน้าจอและระบบพื้นฐาน ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"
FONT_FILE = "THSarabunNew.ttf"

def get_now_th():
    """ดึงเวลาปัจจุบันของประเทศไทย"""
    return datetime.now(pytz.timezone('Asia/Bangkok'))

# ป้องกัน AttributeError โดยประกาศ Session State เริ่มต้น
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'submitted_id' not in st.session_state:
    st.session_state.submitted_id = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = get_now_th()
if 'selected_case_id' not in st.session_state:
    st.session_state.selected_case_id = None

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    """ฟังก์ชันลบคำว่า nan ออกจากช่องกรอกข้อมูล"""
    if pd.isna(val) or str(val).lower() == "nan" or str(val) == "":
        return ""
    return str(val)

# --- 🔑 2. ข้อมูลบัญชีและระบบสิทธิ์ ---
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

if st.session_state.current_user:
    elapsed = (get_now_th() - st.session_state.last_activity).total_seconds()
    if elapsed > 1800: # 30 นาที
        st.session_state.current_user = None
        st.rerun()
    else:
        st.session_state.last_activity = get_now_th()

# --- 📄 3. ฟังก์ชันสร้าง PDF (แบบทางการพร้อมช่องลงชื่อ 5 ฝ่าย + Footer) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        if not os.path.exists(FONT_FILE): return "MISSING_FONT"
        pdf.add_font('ThaiFont', '', FONT_FILE)
        
        if os.path.exists(LOGO_FILE):
            pdf.image(LOGO_FILE, x=15, y=12, w=18)
        
        pdf.set_y(15); pdf.set_font('ThaiFont', '', 20)
        pdf.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16); pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน", ln=True, align='C')
        pdf.ln(5); pdf.line(15, pdf.get_y(), 195, pdf.get_y()); pdf.ln(8)
        
        pdf.set_font('ThaiFont', '', 14)
        pdf.cell(90, 8, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}")
        pdf.cell(90, 8, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", align='R', ln=True)
        pdf.ln(5)
        pdf.multi_cell(0, 8, txt=f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')} | สถานที่: {row_data.get('Location', '-')}")
        pdf.multi_cell(0, 8, txt=f"รายละเอียดเหตุการณ์: {row_data.get('Details', '-')}")
        
        pdf.ln(5); pdf.set_font('ThaiFont', '', 15); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14); pdf.multi_cell(0, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        # --- ✍️ ส่วนลงชื่อ 5 ฝ่าย (จัดแถวละ 2 คน และคนสุดท้ายกึ่งกลาง) ---
        pdf.ln(10)
        pdf.set_font('ThaiFont', '', 14)
        
        # แถวที่ 1: ผู้เสียหาย และ ผู้ถูกกล่าวหา
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", align='C')
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Victim'))} )", align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Accused'))} )", ln=True, align='C')
        pdf.cell(90, 8, txt="ผู้เสียหาย", align='C')
        pdf.cell(90, 8, txt="ผู้ถูกกล่าวหา", ln=True, align='C')
        pdf.ln(5)

        # แถวที่ 2: ตำรวจนักเรียนผู้สอบสวน และ พยาน
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", align='C')
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Student_Police_Investigator'))} )", align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Witness'))} )", ln=True, align='C')
        pdf.cell(90, 8, txt="ตำรวจนักเรียนผู้สอบสวน", align='C')
        pdf.cell(90, 8, txt="พยาน", ln=True, align='C')
        pdf.ln(5)

        # แถวที่ 3: ครูผู้สอบสวน
        pdf.cell(0, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(0, 8, txt=f"( {clean_val(row_data.get('Teacher_Investigator'))} )", ln=True, align='C')
        pdf.cell(0, 8, txt="ครูผู้สอบสวน / หัวหน้างานปกครอง", ln=True, align='C')

        # --- 🕒 ส่วน Footer มุมขวาล่าง ---
        pdf.set_y(-20); pdf.set_font('ThaiFont', '', 10)
        now_str = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
        printer = st.session_state.current_user['name'] if st.session_state.current_user else "System"
        pdf.cell(0, 5, txt=f"พิมพ์โดย: {printer} | วันเวลาที่พิมพ์: {now_str}", align='R')
        
        return pdf.output()
    except Exception as e: return str(e)

# --- 📋 4. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col_h2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        tab1, tab2 = st.tabs(["🔎 รายการทั้งหมด", "🛠 สอบสวนและบันทึกผล"])
        
        with tab1:
            # ปรับแต่งตาราง: หัวข้อภาษาไทย และนำเลขเคสขึ้นต้น
            st.write("📌 คลิกเลือกเลขเคสใน Tab สอบสวนเพื่อดูรายละเอียดเชิงลึก")
            display_df = df[['Report_ID', 'Timestamp', 'Incident_Type', 'Location', 'Status']].copy()
            display_df.columns = ['เลขที่รับแจ้ง', 'วันเวลาที่แจ้ง', 'ประเภทเหตุ', 'สถานที่', 'สถานะปัจจุบัน']
            st.dataframe(display_df.iloc[::-1], use_container_width=True)

        with tab2:
            ids = df['Report_ID'].dropna().unique().tolist()
            sid = st.selectbox("เลือกเลขที่รับแจ้ง:", ids, index=ids.index(st.session_state.selected_case_id) if st.session_state.selected_case_id in ids else 0)
            st.session_state.selected_case_id = sid
            sel = df[df['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]; row = sel.iloc[0]
                is_admin = user['role'] == 'admin'
                with st.container(border=True):
                    st.subheader(f"🔢 เลขที่รับแจ้ง: {sid}")
                    col_det1, col_det2 = st.columns([2, 1])
                    with col_det1:
                        st.write(f"👤 **ผู้แจ้ง:** {row['Reporter']} | 🚨 **ประเภท:** {row['Incident_Type']}")
                        st.write(f"📝 **รายละเอียดเหตุการณ์:** {row['Details']}")
                    with col_det2:
                        img_data = clean_val(row.get('Image_Data'))
                        if img_data:
                            try:
                                decoded_img = base64.b64decode(img_data)
                                st.image(decoded_img, caption="📸 ภาพประกอบเหตุการณ์", use_container_width=True)
                            except: st.info("ไม่สามารถแสดงรูปภาพได้")
                    
                    st.markdown("---")
                    st.write("📋 **บันทึกผลการสอบสวน**")
                    c1, c2 = st.columns(2)
                    with c1:
                        v_vic = st.text_input("ผู้เสียหาย", value=clean_val(row.get('Victim')), disabled=not is_admin, placeholder="ระบุชื่อผู้เสียหาย...")
                        v_acc = st.text_input("ผู้ถูกกล่าวหา", value=clean_val(row.get('Accused')), disabled=not is_admin, placeholder="ระบุชื่อผู้ถูกกล่าวหา...")
                        v_wit = st.text_input("พยาน", value=clean_val(row.get('Witness')), disabled=not is_admin, placeholder="ระบุชื่อพยาน (ถ้ามี)...")
                    with c2:
                        v_tea = st.text_input("ครูผู้สอบสวน", value=clean_val(row.get('Teacher_Investigator')), disabled=not is_admin, placeholder="ระบุชื่อครู...")
                        v_stu = st.text_input("ตำรวจนักเรียนสอบสวน", value=clean_val(row.get('Student_Police_Investigator')), disabled=not is_admin, placeholder="ระบุชื่อตำรวจนักเรียน...")
                        opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                        v_sta = st.selectbox("สถานะ", opts, index=opts.index(row['Status']) if row['Status'] in opts else 0, disabled=not is_admin)
                    
                    v_stmt = st.text_area("บันทึกคำให้การ/ผลการดำเนินการ", value=clean_val(row.get('Statement')), disabled=not is_admin, placeholder="ระบุรายละเอียดการสอบสวนและคำให้การ...")

                    if is_admin:
                        if st.button("💾 บันทึกการสอบสวน", type="primary", use_container_width=True):
                            df.at[idx, 'Victim'], df.at[idx, 'Accused'], df.at[idx, 'Witness'] = v_vic, v_acc, v_wit
                            df.at[idx, 'Teacher_Investigator'], df.at[idx, 'Student_Police_Investigator'] = v_tea, v_stu
                            df.at[idx, 'Status'], df.at[idx, 'Statement'], df.at[idx, 'Handled_By'] = v_sta, v_stmt, user['name']
                            conn.update(data=df)
                            st.success("✅ ระบบบันทึกข้อมูลการสอบสวนเรียบร้อยแล้ว!") # ยืนยันการบันทึก
                            st.rerun()
                    else: st.info("🔒 เฉพาะแอดมินเท่านั้นที่สามารถบันทึกข้อมูลได้")
                    
                    pdf_bytes = create_pdf(df.loc[idx])
                    if isinstance(pdf_bytes, (bytes, bytearray)):
                        st.download_button("📥 พิมพ์ PDF ใบสรุปผลสอบสวน", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5])
        with c2: st.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้งของคุณคือ: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.form("report_form"):
            st.info("กรุณากรอกข้อมูลฟิลด์บังคับ (*) ให้ครบถ้วน")
            c1, c2 = st.columns(2)
            with c1:
                rep = st.text_input("ชื่อผู้แจ้ง *")
                typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            with c2:
                loc = st.text_input("สถานที่เกิดเหตุ *")
                img_file = st.file_uploader("แนบรูปภาพเหตุการณ์ (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
            det = st.text_area("รายละเอียดเหตุการณ์")
            
            if st.form_submit_button("📤 ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
                if rep and typ and loc: # บังคับกรอกฟิลด์สำคัญ
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    img_b64 = ""
                    if img_file:
                        try:
                            image = Image.open(img_file); image.thumbnail((400, 400))
                            buffer = io.BytesIO(); image.save(buffer, format="JPEG", quality=70)
                            img_b64 = base64.b64encode(buffer.getvalue()).decode()
                        except: pass

                    df_old = conn.read(ttl=0)
                    new_r = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": img_b64}])
                    conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                    st.session_state.submitted_id = rid
                    st.rerun()
                else: st.error("⚠️ กรุณากรอกชื่อผู้แจ้ง, สถานที่ และประเภทเหตุให้ครบถ้วน")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.session_state.last_activity = get_now_th()
                st.rerun()
            else: st.error("❌ รหัสผ่านไม่ถูกต้อง")

# --- 🚀 6. รันระบบ ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
