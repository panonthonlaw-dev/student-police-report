import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import random
import os
import base64
import time
import math
from fpdf import FPDF
from PIL import Image
import io

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบแจ้งความตำรวจนักเรียน", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"
FONT_FILE = "THSarabunNew.ttf"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

# ฟังก์ชันย่อรูปภาพ
def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        img.thumbnail((500, 500))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

# --- 2. Class PDF ---
class ReportPDF(FPDF):
    def header(self):
        if os.path.exists(FONT_FILE):
            self.add_font('ThaiFont', '', FONT_FILE)
            self.set_font('ThaiFont', '', 20)
        if os.path.exists(LOGO_FILE):
            self.image(LOGO_FILE, x=20, y=12, w=20)
        self.set_y(15)
        self.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='C')
        self.set_font('ThaiFont', '', 16)
        self.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน", ln=True, align='C')
        self.ln(5)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(8)

def create_pdf(row_data):
    try:
        if not os.path.exists(FONT_FILE): return f"MISSING_FONT"
        pdf = ReportPDF()
        pdf.set_margins(20, 20, 20)
        pdf.add_page()
        epw = pdf.w - 2 * pdf.l_margin
        pdf.add_font('ThaiFont', '', FONT_FILE)
        pdf.set_font('ThaiFont', '', 14)
        
        pdf.cell(epw*0.6, 8, txt=f"เลขที่รับแจ้ง: {clean_val(row_data.get('Report_ID'))}")
        pdf.cell(epw*0.4, 8, txt=f"วันที่แจ้ง: {clean_val(row_data.get('Timestamp'))}", ln=True, align='R')
        pdf.multi_cell(epw, 8, txt=f"ประเภท: {clean_val(row_data.get('Incident_Type'))} | สถานที่: {clean_val(row_data.get('Location'))}")
        pdf.multi_cell(epw, 8, txt=f"รายละเอียดเดิม: {clean_val(row_data.get('Details'))}")
        
        pdf.ln(5)
        pdf.set_font('ThaiFont', '', 16); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(epw, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        ev_img = clean_val(row_data.get('Evidence_Image'))
        if ev_img:
            pdf.ln(5)
            pdf.cell(0, 8, txt="รูปพยานหลักฐานประกอบการสอบสวน:", ln=True)
            img_data = base64.b64decode(ev_img)
            img_io = io.BytesIO(img_data)
            pdf.image(img_io, w=80)

        pdf.ln(10)
        if pdf.get_y() > 220: pdf.add_page()
        col_w = epw / 2
        y_sign = pdf.get_y()
        pdf.set_xy(20, y_sign)
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Victim'))} )", align='C', ln=0)
        pdf.set_xy(20 + col_w, y_sign)
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Accused'))} )", align='C', ln=1)
        pdf.cell(epw, 15, txt=f"ครูผู้สอบสวน: {clean_val(row_data.get('Teacher_Investigator'))}", align='C', ln=1)

        return pdf.output()
    except Exception as e: return f"ERROR: {str(e)}"

# --- 3. ระบบจัดการ State & Helper ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", ""] or val is None: return ""
    return str(val).strip()

# --- 4. ฟังก์ชันจัดรูปแบบรายการ (The "Beautiful" List) ---
def render_case_list(df_subset, list_type):
    c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
    c1.markdown("**เลขที่รับแจ้ง**")
    c2.markdown("**วันเวลา**")
    c3.markdown("**ประเภทเหตุ**")
    c4.markdown("**สถานะ**")
    st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

    if df_subset.empty:
        st.caption("ไม่มีรายการ")
        return

    for index, row in df_subset.iterrows():
        raw_rid = str(row.get('Report_ID', '')).strip()
        rid_label = raw_rid if raw_rid else "⚠️ ไม่พบเลข"
        has_result = (clean_val(row.get('Status')) == "ดำเนินการเรียบร้อย")
        
        cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
        with cc1:
            btn_txt = f"✅ {rid_label}" if has_result else f"📝 {rid_label}"
            st.button(btn_txt, key=f"btn_{list_type}_{index}", use_container_width=True, on_click=view_case, args=(raw_rid,))
        with cc2: st.write(row.get('Timestamp', '-'))
        with cc3: st.write(row.get('Incident_Type', '-'))
        with cc4:
            if has_result: st.markdown(f"<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True)
            else: st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ รอสอบสวน</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

# --- 5. Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col_h2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None; st.rerun()

    try:
        df = conn.read(ttl="1m")
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        if st.session_state.view_mode == "list":
            # กรองข้อมูล
            df_pending = df[df['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
            df_finished = df[df['Status'] == "ดำเนินการเรียบร้อย"][::-1]

            st.markdown("<h4 style='color:#1E3A8A;'>⏳ รายการที่รอการดำเนินการ</h4>", unsafe_allow_html=True)
            render_case_list(df_pending.head(20), "pending")

            st.markdown("<br><h4 style='color:#2e7d32;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
            render_case_list(df_finished.head(20), "finished")

        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            sel = df[df['Report_ID'] == sid]
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list)
                
                # ระบบล็อค
                current_status = clean_val(row.get('Status'))
                is_admin = user.get('role') == 'admin'
                is_finished = (current_status == "ดำเนินการเรียบร้อย")
                is_locked = True if (is_finished and st.session_state.unlock_password != "Patwit1510") else False
                if not is_admin: is_locked = True

                with st.container(border=True):
                    st.markdown(f"### 📝 เลขที่รับแจ้ง: {sid}")
                    st.write(f"**ผู้แจ้ง:** {row.get('Reporter')} | **สถานที่:** {row.get('Location')}")
                    st.info(f"**รายละเอียด:** {row.get('Details')}")
                    if clean_val(row.get('Image_Data')):
                        st.image(base64.b64decode(row['Image_Data']), width=400, caption="หลักฐานจากผู้แจ้ง")

                    st.markdown("---")
                    st.write("#### ✍️ บันทึกผลการสอบสวน")
                    
                    if is_locked and is_finished and is_admin:
                        st.markdown("<div style='color:red;'>🔒 เคสนี้ดำเนินการเรียบร้อยแล้ว (แอดมินใส่รหัสปลดล็อคเพื่อแก้ไข)</div>", unsafe_allow_html=True)
                        cpwd, cbtn = st.columns([3, 1])
                        pwd_in = cpwd.text_input("รหัสปลดล็อค", type="password")
                        if cbtn.button("ปลดล็อค"):
                            if pwd_in == "Patwit1510": st.session_state.unlock_password = "Patwit1510"; st.rerun()

                    v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=is_locked)
                    v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=is_locked)
                    v_stmt = st.text_area("ผลการดำเนินการสอบสวน *", value=clean_val(row.get('Statement')), disabled=is_locked)
                    
                    ev_img_file = st.file_uploader("📸 แนบรูปหลักฐานการสอบสวนเพิ่มเติม", type=['jpg','png'], disabled=is_locked)
                    if clean_val(row.get('Evidence_Image')):
                        st.image(base64.b64decode(row['Evidence_Image']), width=200, caption="รูปหลักฐานปัจจุบัน")

                    opts = ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"]
                    v_sta = st.selectbox("สถานะปัจจุบัน", opts, index=opts.index(current_status) if current_status in opts else 0, disabled=is_locked)

                    if not is_locked:
                        if st.button("💾 บันทึกข้อมูลและประวัติ", type="primary", use_container_width=True):
                            final_img = process_image(ev_img_file) if ev_img_file else row.get('Evidence_Image')
                            new_log = f"[{get_now_th().strftime('%d/%m/%Y %H:%M')}] แก้ไขโดย {user['name']}"
                            old_log = clean_val(row.get('Audit_Log'))
                            
                            df.at[idx, 'Victim'] = v_vic
                            df.at[idx, 'Accused'] = v_acc
                            df.at[idx, 'Statement'] = v_stmt
                            df.at[idx, 'Status'] = v_sta
                            df.at[idx, 'Evidence_Image'] = final_img
                            df.at[idx, 'Audit_Log'] = f"{old_log}\n{new_log}" if old_log else new_log
                            
                            conn.update(data=df)
                            st.cache_data.clear()
                            st.success("บันทึกเรียบร้อย!"); time.sleep(1); st.rerun()

                    st.markdown("---")
                    pdf_bytes = create_pdf(row)
                    if "ERROR" not in str(pdf_bytes):
                        st.download_button("🖨️ พิมพ์รายงานสรุปผล (PDF)", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True)
                    
                    with st.expander("📜 ดูประวัติการแก้ไข (Audit Trail)"):
                        st.text(row.get('Audit_Log', 'ไม่มีประวัติ'))

    except Exception as e: st.error(f"Error: {e}")

# --- 6. หน้าหลักแจ้งเหตุ ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]); c2.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งความตำรวจนักเรียน</h1>", unsafe_allow_html=True)
    
    with st.form("report_form"):
        rep = st.text_input("ชื่อผู้แจ้ง *")
        typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สารเสพติด", "อาวุธ", "ลักทรัพย์", "บูลลี่", "อื่นๆ"])
        loc = st.text_input("สถานที่เกิดเหตุ *")
        det = st.text_area("รายละเอียดเหตุการณ์ *")
        img = st.file_uploader("แนบรูปภาพประกอบ (ถ้ามี)", type=['jpg','png'])
        
        if st.form_submit_button("ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
            if rep and loc and det:
                rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                df_old = conn.read(ttl="1m")
                new_data = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": process_image(img)}])
                conn.update(data=pd.concat([df_old, new_data], ignore_index=True))
                st.cache_data.clear()
                st.success(f"ส่งข้อมูลสำเร็จ! รหัสรับแจ้งคือ: {rid}")
            else: st.error("กรุณากรอกข้อมูลให้ครบ")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            accounts = st.secrets.get("officer_accounts", {})
            if pw in accounts:
                st.session_state.current_user = accounts[pw]
                st.rerun()
            else: st.error("รหัสผิด")

# --- รันแอป ---
st.markdown("<style>.main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }</style>", unsafe_allow_html=True)
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"

if st.session_state.current_user: officer_dashboard()
else: main_page()
