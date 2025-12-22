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

# ฟังก์ชันย่อรูปภาพเพื่อประหยัดพื้นที่ Google Sheets
def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        # ปรับขนาดให้เล็กลงแต่ยังชัดเจน (เช่น กว้าง 500px)
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
        
        # รายละเอียดเบื้องต้น
        pdf.cell(epw*0.6, 8, txt=f"เลขที่รับแจ้ง: {clean_val(row_data.get('Report_ID'))}")
        pdf.cell(epw*0.4, 8, txt=f"วันที่แจ้ง: {clean_val(row_data.get('Timestamp'))}", ln=True, align='R')
        pdf.multi_cell(epw, 8, txt=f"ประเภท: {clean_val(row_data.get('Incident_Type'))} | สถานที่: {clean_val(row_data.get('Location'))}")
        pdf.multi_cell(epw, 8, txt=f"รายละเอียดเดิม: {clean_val(row_data.get('Details'))}")
        
        # ผลการสอบสวน
        pdf.ln(5)
        pdf.set_font('ThaiFont', '', 16); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        pdf.multi_cell(epw, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        # แสดงรูปหลักฐาน (ถ้ามี)
        ev_img = clean_val(row_data.get('Evidence_Image'))
        if ev_img:
            pdf.ln(5)
            pdf.cell(0, 8, txt="รูปพยานหลักฐานประกอบการสอบสวน:", ln=True)
            img_data = base64.b64decode(ev_img)
            img_io = io.BytesIO(img_data)
            # วางรูปหลักฐานใน PDF
            pdf.image(img_io, w=60)

        # ลายเซ็น (ปรับตำแหน่ง)
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

# --- 3. ระบบจัดการ State ---
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

# --- 4. Dashboard สำหรับเจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    st.markdown(f"### 🏢 ระบบจัดการ (คุณ{user['name']})")
    
    try:
        df = conn.read(ttl="1m")
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        if st.session_state.view_mode == "list":
            if st.button("🔴 Logout"): 
                st.session_state.current_user = None; st.rerun()
            
            # แบ่งเคส Pending/Finished
            df_pending = df[df['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
            df_finished = df[df['Status'] == "ดำเนินการเรียบร้อย"][::-1]

            st.subheader("⏳ เคสที่รอการจัดการ")
            for i, r in df_pending.head(10).iterrows():
                col1, col2 = st.columns([4, 1])
                col1.write(f"📌 {r['Report_ID']} | {r['Incident_Type']} ({r['Timestamp']})")
                col2.button("จัดการ", key=f"edit_{i}", on_click=view_case, args=(r['Report_ID'],))

            st.subheader("✅ เคสที่ดำเนินการเรียบร้อย")
            st.dataframe(df_finished[['Report_ID', 'Timestamp', 'Incident_Type', 'Status']].head(5))

        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            sel = df[df['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                st.button("⬅️ กลับ", on_click=back_to_list)
                
                # ตรวจสอบสถานะการล็อค
                current_status = clean_val(row.get('Status'))
                is_admin = user.get('role') == 'admin'
                is_finished = (current_status == "ดำเนินการเรียบร้อย")
                is_locked = True if (is_finished and st.session_state.unlock_password != "Patwit1510") else False
                if not is_admin: is_locked = True

                with st.expander("🔍 ข้อมูลเหตุการณ์", expanded=True):
                    st.write(f"**ผู้แจ้ง:** {row.get('Reporter')}")
                    st.write(f"**รายละเอียด:** {row.get('Details')}")
                    if clean_val(row.get('Image_Data')):
                        st.image(base64.b64decode(row['Image_Data']), width=300, caption="รูปจากผู้แจ้ง")

                # ส่วนการสอบสวน
                st.markdown("### ✍️ บันทึกการสอบสวนและพยานหลักฐาน")
                if is_locked: st.warning("🔒 ข้อมูลถูกล็อค (ต้องใช้สิทธิ์แอดมินปลดล็อคเพื่อแก้ไข)")

                v_vic = st.text_input("ผู้เสียหาย", value=clean_val(row.get('Victim')), disabled=is_locked)
                v_acc = st.text_input("ผู้ถูกกล่าวหา", value=clean_val(row.get('Accused')), disabled=is_locked)
                v_stmt = st.text_area("บันทึกผลการดำเนินการ", value=clean_val(row.get('Statement')), disabled=is_locked)
                
                # เพิ่มฟังก์ชันแนบรูปหลักฐาน
                ev_img_file = st.file_uploader("📸 แนบรูปหลักฐานจากการสอบสวน (บ่งบอกว่าเป็นหลักฐาน)", type=['jpg','jpeg','png'], disabled=is_locked)
                if clean_val(row.get('Evidence_Image')):
                    st.image(base64.b64decode(row['Evidence_Image']), width=200, caption="หลักฐานปัจจุบัน")

                v_sta = st.selectbox("สถานะการดำเนินการ", ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"], 
                                     index=["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"].index(current_status) if current_status in ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"] else 0,
                                     disabled=is_locked)

                if not is_locked:
                    if st.button("💾 บันทึกข้อมูลและประวัติ", type="primary"):
                        # จัดการรูปหลักฐาน
                        final_ev_img = process_image(ev_img_file) if ev_img_file else row.get('Evidence_Image')
                        
                        # บันทึก Audit Log (ใครแก้เมื่อไหร่)
                        new_log = f"[{get_now_th().strftime('%d/%m/%Y %H:%M')}] แก้ไขโดย {user['name']}"
                        old_log = clean_val(row.get('Audit_Log'))
                        
                        df.at[idx, 'Victim'] = v_vic
                        df.at[idx, 'Accused'] = v_acc
                        df.at[idx, 'Statement'] = v_stmt
                        df.at[idx, 'Status'] = v_sta
                        df.at[idx, 'Evidence_Image'] = final_ev_img
                        df.at[idx, 'Audit_Log'] = f"{old_log}\n{new_log}" if old_log else new_log
                        
                        conn.update(data=df)
                        st.cache_data.clear()
                        st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()

                # ปุ่ม PDF
                st.markdown("---")
                pdf_bytes = create_pdf(row)
                if "ERROR" not in str(pdf_bytes):
                    st.download_button("🖨️ พิมพ์รายงานสรุปผล (PDF)", data=bytes(pdf_bytes), file_name=f"Report_{sid}.pdf", mime="application/pdf")

                # ประวัติการแก้ไข (Audit Trail)
                with st.expander("📜 ประวัติการแก้ไขระบบ (Audit Trail)"):
                    st.text(row.get('Audit_Log', 'ไม่มีประวัติ'))

    except Exception as e: st.error(f"ระบบขัดข้อง: {e}")

# --- 5. หน้าแจ้งเหตุสำหรับนักเรียน ---
def main_page():
    st.markdown("<h1 style='text-align: center;'>👮‍♂️ ระบบแจ้งความตำรวจนักเรียน</h1>", unsafe_allow_html=True)
    with st.form("report_form"):
        rep = st.text_input("ชื่อผู้แจ้ง *")
        typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สารเสพติด", "อาวุธ", "ลักทรัพย์", "บูลลี่", "อื่นๆ"])
        loc = st.text_input("สถานที่เกิดเหตุ *")
        det = st.text_area("รายละเอียดเหตุการณ์ *")
        img = st.file_uploader("แนบรูปภาพหลักฐาน (ถ้ามี)", type=['jpg','png'])
        
        if st.form_submit_button("ส่งข้อมูลแจ้งเหตุ"):
            if rep and loc and det:
                rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                img_b64 = process_image(img) if img else ""
                
                df_old = conn.read(ttl="1m")
                new_data = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": img_b64}])
                conn.update(data=pd.concat([df_old, new_data], ignore_index=True))
                st.cache_data.clear()
                st.success(f"ส่งข้อมูลสำเร็จ! เลขที่รับแจ้งของคุณคือ: {rid}")
            else: st.error("กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบ")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            accounts = st.secrets.get("officer_accounts", {})
            if pw in accounts:
                st.session_state.current_user = accounts[pw]
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")

# --- รันระบบ ---
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"

if st.session_state.current_user: officer_dashboard()
else: main_page()
