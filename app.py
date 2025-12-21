import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random
import os
import base64  # เพิ่มสำหรับการจัดการรูปภาพ
from fpdf import FPDF
from PIL import Image
import io

# --- 1. ตั้งค่าหน้าจอและระบบพื้นฐาน ---
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

# --- 🔑 2. ระบบจัดการสิทธิ์และ Timeout 30 นาที ---
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

# --- 📄 3. ฟังก์ชันสร้าง PDF (แบบทางการพร้อมช่องลงชื่อ 5 ฝ่าย) ---
def create_pdf(row_data):
    try:
        pdf = FPDF()
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        if not os.path.exists(FONT_FILE): return "MISSING_FONT"
        pdf.add_font('ThaiFont', '', FONT_FILE)
        if os.path.exists(LOGO_FILE): pdf.image(LOGO_FILE, x=15, y=12, w=18)
        
        pdf.set_y(15); pdf.set_font('ThaiFont', '', 20)
        pdf.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        pdf.set_font('ThaiFont', '', 16); pdf.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน", ln=True, align='C')
        pdf.ln(5); pdf.line(15, pdf.get_y(), 195, pdf.get_y()); pdf.ln(8)
        
        pdf.set_font('ThaiFont', '', 14)
        pdf.cell(90, 8, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}")
        pdf.cell(90, 8, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", align='R', ln=True)
        pdf.ln(5); pdf.multi_cell(0, 8, txt=f"รายละเอียดเหตุการณ์เดิม: {row_data.get('Details', '-')}")
        
        pdf.ln(10); pdf.set_font('ThaiFont', '', 15); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14); pdf.multi_cell(0, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        # ส่วนลงชื่อ... (ย่อส่วน)
        pdf.set_y(-25); pdf.set_font('ThaiFont', '', 10)
        now_str = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
        printer = st.session_state.current_user['name'] if st.session_state.current_user else "System"
        pdf.cell(0, 5, txt=f"พิมพ์โดย: {printer} | เวลา: {now_str}", align='R')
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
        tab1, tab2 = st.tabs(["🔎 รายการแจ้งเหตุทั้งหมด", "🛠 สอบสวนและบันทึกผล"])
        
        with tab1:
            st.write("📌 คลิกเลือกเลขที่รับแจ้งเพื่อดูรายละเอียดที่ Tab สอบสวน")
            display_df = df[['Report_ID', 'Timestamp', 'Incident_Type', 'Location', 'Status']].copy()
            display_df.columns = ['เลขที่รับแจ้ง', 'วันเวลา', 'ประเภทเหตุ', 'สถานที่', 'สถานะ']
            st.dataframe(display_df.iloc[::-1], use_container_width=True)

        with tab2:
            ids = df['Report_ID'].dropna().unique().tolist()
            # ระบบเชื่อมโยงเลขเคส
            sid = st.selectbox("เลือกเลขที่รับแจ้ง:", ids, index=ids.index(st.session_state.selected_case_id) if st.session_state.selected_case_id in ids else 0)
            st.session_state.selected_case_id = sid
            sel = df[df['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]; row = sel.iloc[0]
                is_admin = user['role'] == 'admin'
                with st.container(border=True):
                    st.subheader(f"🔢 รายละเอียดเคส: {sid}")
                    col_info1, col_info2 = st.columns([2, 1])
                    with col_info1:
                        st.write(f"👤 **ผู้แจ้ง:** {row['Reporter']} | 🚨 **ประเภท:** {row['Incident_Type']}")
                        st.write(f"📝 **รายละเอียด:** {row['Details']}")
                    with col_info2:
                        # --- ระบบแสดงภาพที่แนบมา ---
                        img_data = clean_val(row.get('Image_Data'))
                        if img_data:
                            st.write("📸 **ภาพประกอบเหตุการณ์:**")
                            try:
                                decoded_img = base64.b64decode(img_data)
                                st.image(decoded_img, use_container_width=True)
                            except: st.warning("ไม่สามารถโหลดภาพได้")
                        else: st.info("ไม่มีภาพประกอบ")

                    st.markdown("---")
                    st.write("📋 **บันทึกผลการสอบสวนเพิ่มเติม**")
                    c1, c2 = st.columns(2)
                    with c1:
                        v_vic = st.text_input("ผู้เสียหาย", value=clean_val(row.get('Victim')), disabled=not is_admin)
                        v_acc = st.text_input("ผู้ถูกกล่าวหา", value=clean_val(row.get('Accused')), disabled=not is_admin)
                        v_wit = st.text_input("พยาน", value=clean_val(row.get('Witness')), disabled=not is_admin)
                    with c2:
                        v_tea = st.text_input("ครูผู้สอบสวน", value=clean_val(row.get('Teacher_Investigator')), disabled=not is_admin)
                        v_stu = st.text_input("ตำรวจนักเรียน", value=clean_val(row.get('Student_Police_Investigator')), disabled=not is_admin)
                        opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                        v_sta = st.selectbox("สถานะ", opts, index=opts.index(row['Status']) if row['Status'] in opts else 0, disabled=not is_admin)
                    v_stmt = st.text_area("บันทึกคำให้การ/ผลสอบสวน", value=clean_val(row.get('Statement')), disabled=not is_admin)

                    if is_admin:
                        if st.button("💾 บันทึกการสอบสวน", type="primary", use_container_width=True):
                            df.at[idx, 'Victim'], df.at[idx, 'Accused'], df.at[idx, 'Witness'] = v_vic, v_acc, v_wit
                            df.at[idx, 'Teacher_Investigator'], df.at[idx, 'Student_Police_Investigator'] = v_tea, v_stu
                            df.at[idx, 'Status'], df.at[idx, 'Statement'], df.at[idx, 'Handled_By'] = v_sta, v_stmt, user['name']
                            conn.update(data=df)
                            st.success("✅ ระบบบันทึกข้อมูลเรียบร้อยแล้ว!")
                            st.rerun()
                    else: st.info("🔒 อ่านข้อมูลได้อย่างเดียว")
                    
                    pdf_bytes = create_pdf(df.loc[idx])
                    if isinstance(pdf_bytes, (bytes, bytearray)):
                        st.download_button("📥 พิมพ์ PDF สรุปผล", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

# --- 📝 5. หน้าจอหลัก (แจ้งเหตุพร้อมแนบรูปภาพและฟิลด์บังคับ) ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5])
        with c2: st.image(LOGO_FILE, width=100)

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.form("report_form"):
            st.info("กรุณากรอกข้อมูลในช่องที่มีเครื่องหมาย * ให้ครบถ้วน")
            c1, c2 = st.columns(2)
            with c1:
                rep = st.text_input("ชื่อผู้แจ้ง *")
                typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            with c2:
                loc = st.text_input("สถานที่เกิดเหตุ *")
                img_file = st.file_uploader("แนบรูปภาพเหตุการณ์ (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
            det = st.text_area("รายละเอียดเหตุการณ์")
            
            if st.form_submit_button("📤 ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
                if rep and typ and loc: # ตรวจสอบฟิลด์บังคับ
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    
                    # จัดการรูปภาพ (บีบอัดและแปลงเป็น Base64)
                    img_b64 = ""
                    if img_file:
                        try:
                            image = Image.open(img_file)
                            image.thumbnail((400, 400)) # ย่อขนาดเพื่อไม่ให้เกินขีดจำกัด Google Sheets
                            buffer = io.BytesIO()
                            image.save(buffer, format="JPEG", quality=70)
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

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
