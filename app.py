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
st.set_page_config(page_title="ระบบแจ้งความตำรวจนักเรียน ", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"
FONT_FILE = "THSarabunNew.ttf"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

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

    def footer(self):
        self.set_y(-15)
        if os.path.exists(FONT_FILE):
            self.add_font('ThaiFont', '', FONT_FILE)
            self.set_font('ThaiFont', '', 10)
        printer = "System"
        if 'current_user' in st.session_state and st.session_state.current_user:
            printer = st.session_state.current_user['name']
        now_str = datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%d/%m/%Y %H:%M:%S")
        page_width = self.w - 2 * self.l_margin
        self.set_x(self.l_margin)
        self.cell(page_width, 10, txt=f"พิมพ์โดย: {printer} | เวลา: {now_str} | หน้า {self.page_no()}", align='R')

def create_pdf(row_data):
    try:
        if not os.path.exists(FONT_FILE): return f"MISSING_FONT: ไม่พบไฟล์ {FONT_FILE}"
        pdf = ReportPDF()
        pdf.set_margins(20, 20, 20) 
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        epw = pdf.w - 2 * pdf.l_margin 
        pdf.add_font('ThaiFont', '', FONT_FILE)
        pdf.set_font('ThaiFont', '', 14)
        
        col1_w = epw * 0.60 
        col2_w = epw * 0.40
        pdf.cell(col1_w, 8, txt=f"เลขที่รับแจ้ง: {clean_val(row_data.get('Report_ID'))}")
        pdf.cell(col2_w, 8, txt=f"วันที่แจ้งเหตุ: {clean_val(row_data.get('Timestamp'))}", align='R', ln=True)
        pdf.ln(2)
        
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 8, txt=f"ประเภทเหตุ: {clean_val(row_data.get('Incident_Type'))} | สถานที่: {clean_val(row_data.get('Location'))}")
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 8, txt=f"รายละเอียดเหตุการณ์เดิม: {clean_val(row_data.get('Details'))}")
        
        pdf.ln(5)
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 8, txt=clean_val(row_data.get('Statement')), border=1)
        pdf.ln(10)
        
        if pdf.get_y() > 220: pdf.add_page()
        col_w = epw / 2
        
        y_start = pdf.get_y()
        pdf.set_xy(pdf.l_margin, y_start)
        pdf.cell(col_w, 8, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Victim'))} )", align='C', ln=1)
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.cell(col_w, 8, txt="ผู้เสียหาย", align='C', ln=1)
        
        pdf.set_xy(pdf.l_margin + col_w, y_start)
        pdf.cell(col_w, 8, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_xy(pdf.l_margin + col_w, pdf.get_y())
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Accused'))} )", align='C', ln=1)
        pdf.set_xy(pdf.l_margin + col_w, pdf.get_y())
        pdf.cell(col_w, 8, txt="ผู้ถูกกล่าวหา", align='C', ln=1)
        
        pdf.ln(8)
        
        y_start = pdf.get_y()
        pdf.set_xy(pdf.l_margin, y_start)
        pdf.cell(col_w, 8, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Student_Police_Investigator'))} )", align='C', ln=1)
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.cell(col_w, 8, txt="ตำรวจนักเรียนผู้สอบสวน", align='C', ln=1)
        
        pdf.set_xy(pdf.l_margin + col_w, y_start)
        pdf.cell(col_w, 8, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_xy(pdf.l_margin + col_w, pdf.get_y())
        pdf.cell(col_w, 8, txt=f"( {clean_val(row_data.get('Witness'))} )", align='C', ln=1)
        pdf.set_xy(pdf.l_margin + col_w, pdf.get_y())
        pdf.cell(col_w, 8, txt="พยาน", align='C', ln=1)
        
        pdf.ln(8)
        pdf.cell(epw, 8, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.cell(epw, 8, txt=f"( {clean_val(row_data.get('Teacher_Investigator'))} )", align='C', ln=1)
        pdf.cell(epw, 8, txt="ครูผู้สอบสวน / หัวหน้างานปกครอง", align='C', ln=1)

        return pdf.output()
    except Exception as e: return f"ERROR: {str(e)}"

# --- 3. ระบบจัดการ State & Pagination ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

# [FIX] Callback function เพื่อล้างค่าค้นหาอย่างปลอดภัย
def clear_search_callback():
    st.session_state.search_query = ""

# Pagination Helper
def get_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    current_page = st.session_state[key]
    total_pages = math.ceil(total_items / limit)
    if total_pages == 0: total_pages = 1
    if current_page > total_pages: 
        current_page = 1
        st.session_state[key] = 1
    
    start_idx = (current_page - 1) * limit
    end_idx = start_idx + limit
    return start_idx, end_idx, current_page, total_pages

# Initialize State
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'submitted_id' not in st.session_state: st.session_state.submitted_id = None
if 'last_activity' not in st.session_state: st.session_state.last_activity = get_now_th()
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'selected_case_id' not in st.session_state: st.session_state.selected_case_id = None
if 'unlock_password' not in st.session_state: st.session_state.unlock_password = ""
# Pagination States
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    div[data-testid="column"] button { width: 100%; border-radius: 8px; font-weight: bold; }
    .locked-warning { color: #856404; background-color: #fff3cd; border-color: #ffeeba; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .section-header { font-size: 18px; font-weight: bold; color: #333; margin-top: 15px; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 2px solid #eee; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", "nat", ""] or val is None: return ""
    return str(val).strip()

# --- 4. ข้อมูลบัญชี ---
DEFAULT_ACCOUNTS = {
    "Patwit1510": {"name": "แอดมินสูงสุด", "role": "admin"},
    "Pencharee001": {"name": "ครูเพ็ญชรีย์ (ปกครอง)", "role": "admin"},
    "Chaiya001": {"name": "ครูไชยา(ปกครอง)", "role": "admin"},
    "Jak001": {"name": "ยามจักร (รปภ.)", "role": "admin"},
    "User01": {"name": "ผู้กำกับ(ตำรวจนักเรียน)", "role": "admin"},
    "User02": {"name": "รองผู้กำกับจราจร(ตำรวจนักเรียน)", "role": "admin"},
    "User03": {"name": "ครูเวร (ตรวจการณ์)", "role": "viewer"},
    "User04": {"name": "ตำรวจนักเรียน", "role": "viewer"}
}
try: OFFICER_ACCOUNTS = st.secrets["officer_accounts"]
except: OFFICER_ACCOUNTS = DEFAULT_ACCOUNTS

if st.session_state.current_user:
    elapsed = (get_now_th() - st.session_state.last_activity).total_seconds()
    if elapsed > 1800:
        st.session_state.current_user = None
        st.session_state.view_mode = "list"
        st.rerun()
    else:
        st.session_state.last_activity = get_now_th()

# --- 5. Dashboard Logic ---
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
        rid_label = raw_rid if raw_rid and raw_rid.lower() not in ["nan", "none", ""] else "⚠️ ไม่พบเลข (กดดู)"
        real_rid = raw_rid
        has_result = clean_val(row.get('Statement')) != ""
        
        cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
        with cc1:
            btn_label = f"✅ {rid_label}" if has_result else f"📝 {rid_label}"
            st.button(btn_label, key=f"btn_{list_type}_{index}", use_container_width=True, on_click=view_case, args=(real_rid,))
        with cc2: st.write(row.get('Timestamp', '-'))
        with cc3: st.write(row.get('Incident_Type', '-'))
        with cc4:
            if has_result: st.markdown(f"<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True)
            else: st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ รอสอบสวน</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ คุณ{user['name']}</div>", unsafe_allow_html=True)
    with col_h2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.view_mode = "list"
            st.session_state.unlock_password = ""
            st.rerun()

    try:
        df = conn.read(ttl=0)
        df.columns = df.columns.str.strip()
        if 'Report_ID' not in df.columns: df['Report_ID'] = ""
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        # --- VIEW MODE: LIST ---
        if st.session_state.view_mode == "list":
            tab_list, tab_stat = st.tabs(["📋 รายการแจ้งเหตุ (แยกสถานะ)", "📊 สถิติภาพรวม"])
            
            with tab_stat:
                st.subheader("📊 สรุปสถิติการแจ้งเหตุ")
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**แยกตามประเภทเหตุ**")
                    st.bar_chart(df['Incident_Type'].value_counts(), color="#FF4B4B")
                with c2:
                    st.write("**แยกตามสถานะ**")
                    st.bar_chart(df['Status'].value_counts(), color="#1E3A8A")

            with tab_list:
                # [FIXED] Search UI: Input + Search Button + Clear Button (Callback)
                st.write("") # Spacer
                c_search, c_btn_search, c_btn_clear = st.columns([3, 1, 1])
                
                with c_search:
                    search_q = st.text_input("ค้นหา (เลขเคส/ชื่อ/รายละเอียด)", placeholder="พิมพ์เพื่อค้นหา...", key="search_query", label_visibility="collapsed")
                
                with c_btn_search:
                    st.button("🔍 ค้นหา", use_container_width=True) # ปุ่มนี้กดแล้วจะ rerun อัตโนมัติ เป็นการ trigger การค้นหา
                
                with c_btn_clear:
                    # ใช้ on_click เพื่อเรียกฟังก์ชันล้างค่าก่อน render ใหม่ ทำให้ไม่ Error
                    st.button("❌ ล้าง", on_click=clear_search_callback, use_container_width=True)
                
                # Filter Logic
                filtered_df = df.copy()
                if search_q:
                    filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                filtered_df = filtered_df.iloc[::-1]

                # Split Data
                df_pending = filtered_df[filtered_df['Statement'].apply(clean_val) == ""]
                df_finished = filtered_df[filtered_df['Statement'].apply(clean_val) != ""]

                # --- Section 1: Pending ---
                st.markdown("<div class='section-header'>⏳ เคสที่ยังไม่เรียบร้อย (รอสอบสวน)</div>", unsafe_allow_html=True)
                start_p, end_p, curr_p, tot_p = get_pagination('page_pending', len(df_pending), 5)
                render_case_list(df_pending.iloc[start_p:end_p], "pending")
                
                if tot_p > 1:
                    cp1, cp2, cp3 = st.columns([1, 2, 1])
                    with cp1: 
                        if st.button("⬅️ ก่อนหน้า", key="prev_p", disabled=(curr_p==1)): 
                            st.session_state.page_pending -= 1; st.rerun()
                    with cp2: st.markdown(f"<div style='text-align:center'>หน้า {curr_p} / {tot_p}</div>", unsafe_allow_html=True)
                    with cp3: 
                        if st.button("ถัดไป ➡️", key="next_p", disabled=(curr_p==tot_p)): 
                            st.session_state.page_pending += 1; st.rerun()

                # --- Section 2: Finished ---
                st.markdown("<div class='section-header' style='color:#2e7d32;'>✅ เคสที่เรียบร้อยแล้ว (มีผลสอบสวน)</div>", unsafe_allow_html=True)
                start_f, end_f, curr_f, tot_f = get_pagination('page_finished', len(df_finished), 5)
                render_case_list(df_finished.iloc[start_f:end_f], "finished")

                if tot_f > 1:
                    cf1, cf2, cf3 = st.columns([1, 2, 1])
                    with cf1: 
                        if st.button("⬅️ ก่อนหน้า", key="prev_f", disabled=(curr_f==1)): 
                            st.session_state.page_finished -= 1; st.rerun()
                    with cf2: st.markdown(f"<div style='text-align:center'>หน้า {curr_f} / {tot_f}</div>", unsafe_allow_html=True)
                    with cf3: 
                        if st.button("ถัดไป ➡️", key="next_f", disabled=(curr_f==tot_f)): 
                            st.session_state.page_finished += 1; st.rerun()

        # --- VIEW MODE: DETAIL ---
        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            sel = df[df['Report_ID'] == sid]
            if sid == "" and sel.empty: sel = df[df['Report_ID'] == ""]

            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                
                st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list)
                st.markdown(f"### 📝 รายละเอียดเคส: {sid if sid else '(ไม่มีเลข)'}")
                is_admin = user['role'] == 'admin'

                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**ผู้แจ้ง:** {row.get('Reporter', '-')}")
                        st.write(f"**ประเภท:** {row.get('Incident_Type', '-')} | **สถานที่:** {row.get('Location', '-')}")
                        st.info(f"**รายละเอียด:** {row.get('Details', '-')}")
                    with c2:
                        img_data = clean_val(row.get('Image_Data'))
                        if img_data:
                            try:
                                decoded_img = base64.b64decode(img_data)
                                st.image(decoded_img, caption="หลักฐาน", use_container_width=True)
                            except: st.error("รูปภาพเสียหาย")
                        else: st.caption("ไม่มีรูปภาพแนบ")

                    st.markdown("---")
                    
                    # Lock Logic
                    current_status = row.get('Status', 'รอดำเนินการ')
                    is_locked = False
                    is_finished = (current_status == "จัดการแล้ว")
                    
                    if not is_admin: is_locked = True
                    elif is_finished:
                        is_locked = True
                        if st.session_state.unlock_password == "Patwit1510": is_locked = False
                    
                    if is_locked and is_finished and is_admin:
                        st.markdown("<div class='locked-warning'>🔒 เคสปิดงานแล้ว (ใส่รหัสแอดมินเพื่อแก้ไข)</div>", unsafe_allow_html=True)
                        col_pwd, col_btn = st.columns([3, 1])
                        with col_pwd: pwd_input = st.text_input("🔑 รหัสปลดล็อก", type="password", key="pwd_unlock")
                        with col_btn:
                            if st.button("🔓 ปลดล็อก", type="primary", use_container_width=True):
                                if pwd_input == "Patwit1510":
                                    st.session_state.unlock_password = "Patwit1510"
                                    st.toast("ปลดล็อกสำเร็จ!"); st.rerun()
                                else: st.error("รหัสผิด")

                    st.write("#### ✍️ บันทึก/แก้ไข ผลการสอบสวน")
                    f1, f2 = st.columns(2)
                    with f1:
                        v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=is_locked)
                        v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=is_locked)
                        v_wit = st.text_input("พยาน *", value=clean_val(row.get('Witness')), disabled=is_locked)
                    with f2:
                        v_tea = st.text_input("ครูผู้สอบสวน *", value=clean_val(row.get('Teacher_Investigator')), disabled=is_locked)
                        v_stu = st.text_input("ตำรวจนักเรียน *", value=clean_val(row.get('Student_Police_Investigator')), disabled=is_locked)
                        opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                        idx_stat = opts.index(current_status) if current_status in opts else 0
                        v_sta = st.selectbox("สถานะ", opts, index=idx_stat, disabled=is_locked)
                    
                    v_stmt = st.text_area("บันทึกผลการดำเนินการ *", value=clean_val(row.get('Statement')), disabled=is_locked)

                    if not is_locked:
                        is_complete = all([v_vic, v_acc, v_wit, v_tea, v_stu, v_stmt])
                        if st.button("💾 บันทึกข้อมูล", type="secondary", use_container_width=True, disabled=not is_complete):
                            df.at[idx, 'Victim'] = v_vic; df.at[idx, 'Accused'] = v_acc
                            df.at[idx, 'Witness'] = v_wit; df.at[idx, 'Teacher_Investigator'] = v_tea
                            df.at[idx, 'Student_Police_Investigator'] = v_stu; df.at[idx, 'Status'] = v_sta
                            df.at[idx, 'Statement'] = v_stmt; df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.toast("✅ บันทึกเรียบร้อย!"); st.success("บันทึกสำเร็จ!")
                            st.session_state.unlock_password = "" 
                            time.sleep(1.5); st.rerun()
                        if not is_complete: st.caption("⚠️ กรอกข้อมูล (*) ให้ครบเพื่อบันทึก")

                    # ปุ่ม PDF
                    st.markdown("---")
                    st.write("#### 📄 เอกสาร")
                    has_stmt = clean_val(row.get('Statement')) != ""
                    pdf_data = create_pdf(row)
                    if isinstance(pdf_data, (bytes, bytearray)):
                        label = "🖨️ พิมพ์เอกสาร (PDF)" if has_stmt else "🖨️ พิมพ์แบบฟอร์มเปล่า"
                        btn_type = "primary" if has_stmt else "secondary"
                        st.download_button(label=label, data=bytes(pdf_data), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True, type=btn_type)
                    else: st.error(f"❌ สร้าง PDF ไม่ได้: {pdf_data}")
            else: st.error("ไม่พบข้อมูล"); st.button("กลับ", on_click=back_to_list)
    except Exception as e: st.error(f"Error: {e}")

# --- 6. หน้าแจ้งเหตุ ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]); c2.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งความตำรวจนักเรียน</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #1E3A8A;'>สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</h5>", unsafe_allow_html=True)
    st.markdown("<h5 style='text-align: center; color: #E02424;'>ข้อมูลทุกท่านเป็นความลับจะไม่มีการเปิดเผยให้คู่กรณีทราบ</h5>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"): st.session_state.submitted_id = None; st.rerun()
    else:
        with st.form("report"):
            c1, c2 = st.columns(2)
            with c1: 
                rep = st.text_input("ชื่อผู้แจ้ง *")
                # เพิ่มระดับชั้นและห้อง
                cr1, cr2 = st.columns(2)
                with cr1: grade = st.selectbox("ระดับชั้น *", ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6"])
                with cr2: room = st.selectbox("ห้อง *", [str(i) for i in range(14)]) # 0-13
                
                typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท/ทำร้ายร่างกาย", "สารเสพติด/บุหรี่ไฟฟ้า/เครื่องดื่มแอลกอฮอ", "อาวุธอันตราย","ลักทรัพย์/ทำลายทรัพย์สิน","บูลลี่/ด่าทอบนโลกออนไลน์","อื่นๆ"])
                                                                            
            with c2: 
                loc = st.text_input("สถานที่เกิดเหตุ *")
                img = st.file_uploader("รูปภาพ (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
            
            # ช่องรายละเอียดพร้อมตัวอย่าง
            det = st.text_area("รายละเอียด *", placeholder="ตัวอย่าง: สูบบุหรี่ไฟฟ้าเมื่อวันที่ 12 ธ.ค. เวลา 8.30 ที่อาคาร 4 ผู้กระทำผิดคือ... (ถ้าทราบแจ้งชื่อ ห้อง)")
            
            st.markdown("---")
            # Checkbox PDPA
            pdpa_accept = st.checkbox("ข้าพเจ้ายินยอมให้ข้อมูลส่วนบุคคลเพื่อใช้ในการดำเนินงานของงานกิจการนักเรียน", value=False)
            st.markdown("<h7 style='text-align:left; color: #E02424;'>และทราบว่าการแจ้งความเท็จเพื่อกลั่นแกล้งผู้อื่นมีความผิดตามประมวลกฎหมายอาญา</h5>", unsafe_allow_html=True)
            
            if st.form_submit_button("ส่งข้อมูล", use_container_width=True):
                if not pdpa_accept:
                    st.error("⚠️ กรุณายอมรับเงื่อนไข PDPA ก่อนส่งข้อมูล")
                elif rep and typ and loc and det:
                    # รวมข้อมูลชั้นห้องไว้ในชื่อผู้แจ้ง
                    reporter_full = f"{rep} (ชั้น {grade}/{room})"
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    img_b64 = ""
                    if img:
                        try:
                            im = Image.open(img); im.thumbnail((400, 400)); buf = io.BytesIO()
                            im.save(buf, format="JPEG"); img_b64 = base64.b64encode(buf.getvalue()).decode()
                        except: pass
                    df_old = conn.read(ttl=0)
                    # บันทึกโดยใช้ reporter_full
                    new_r = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": reporter_full, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": img_b64}])
                    conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                    st.session_state.submitted_id = rid; st.rerun()
                else: st.error("กรุณากรอกข้อมูลให้ครบ")

    st.markdown("---")
    with st.expander("🔐 เจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.session_state.last_activity = get_now_th(); st.rerun()
            else: st.error("รหัสผิด")

if st.session_state.current_user: officer_dashboard()
else: main_page()
