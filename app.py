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

def clear_search_callback():
    st.session_state.search_query = ""

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

# Initialize States
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'submitted_id' not in st.session_state: st.session_state.submitted_id = None
if 'last_activity' not in st.session_state: st.session_state.last_activity = get_now_th()
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'selected_case_id' not in st.session_state: st.session_state.selected_case_id = None
if 'unlock_password' not in st.session_state: st.session_state.unlock_password = ""
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

# --- 4. บัญชีเจ้าหน้าที่ ---
OFFICER_ACCOUNTS = st.secrets.get("officer_accounts", {})

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
        rid_label = raw_rid if raw_rid and raw_rid.lower() not in ["nan", "none", ""] else "⚠️ ไม่พบเลข"
        has_result = clean_val(row.get('Statement')) != ""
        
        cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
        with cc1:
            btn_label = f"✅ {rid_label}" if has_result else f"📝 {rid_label}"
            st.button(btn_label, key=f"btn_{list_type}_{index}", use_container_width=True, on_click=view_case, args=(raw_rid,))
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
            st.rerun()

    try:
        df = conn.read(ttl="1m")
        df.columns = df.columns.str.strip()
        df = df.fillna("")
        if 'Report_ID' not in df.columns: df['Report_ID'] = ""
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        if st.session_state.view_mode == "list":
            tab_list, tab_stat = st.tabs(["📋 รายการแจ้งเหตุ", "📊 สถิติ"])
            
            with tab_list:
                c_search, c_btn_search, c_btn_clear = st.columns([3, 1, 1])
                with c_search:
                    search_q = st.text_input("ค้นหา", placeholder="พิมพ์เพื่อค้นหา...", key="search_query", label_visibility="collapsed")
                with c_btn_search: st.button("🔍 ค้นหา", use_container_width=True)
                with c_btn_clear: st.button("❌ ล้าง", on_click=clear_search_callback, use_container_width=True)
                
                filtered_df = df.copy()
                if search_q:
                    filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                filtered_df = filtered_df.iloc[::-1]
                df_pending = filtered_df[filtered_df['Statement'].apply(clean_val) == ""]
                df_finished = filtered_df[filtered_df['Statement'].apply(clean_val) != ""]

                st.markdown("<div class='section-header'>⏳ รอสอบสวน</div>", unsafe_allow_html=True)
                start_p, end_p, curr_p, tot_p = get_pagination('page_pending', len(df_pending), 5)
                render_case_list(df_pending.iloc[start_p:end_p], "pending")
                
                st.markdown("<div class='section-header' style='color:#2e7d32;'>✅ เรียบร้อยแล้ว</div>", unsafe_allow_html=True)
                start_f, end_f, curr_f, tot_f = get_pagination('page_finished', len(df_finished), 5)
                render_case_list(df_finished.iloc[start_f:end_f], "finished")

        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            sel = df[df['Report_ID'] == sid]
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                st.button("⬅️ กลับ", on_click=back_to_list)
                
                with st.container(border=True):
                    st.write(f"**ผู้แจ้ง:** {row.get('Reporter', '-')}")
                    st.info(f"**รายละเอียด:** {row.get('Details', '-')}")
                    
                    # --- [RESTORATION] ระบบ Lock และสิทธิ์ ---
                    is_admin = user.get('role', 'viewer') == 'admin'
                    current_status = clean_val(row.get('Status', 'รอดำเนินการ'))
                    
                    # ปรับคำ Status ใหม่
                    STATUS_OPTIONS = ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"]
                    # Map ค่าเดิมให้เข้ากับค่าใหม่ (เผื่อข้อมูลเก่า)
                    if current_status == "กำลังจัดการ": current_status = "อยู่ระหว่างการดำเนินการ"
                    elif current_status == "จัดการแล้ว": current_status = "ดำเนินการเรียบร้อย"
                    
                    is_finished = (current_status == "ดำเนินการเรียบร้อย")
                    is_locked = False
                    
                    if not is_admin: is_locked = True
                    elif is_finished:
                        is_locked = True
                        if st.session_state.unlock_password == "Patwit1510": is_locked = False
                    
                    # UI ปลดล็อค
                    if is_locked and is_finished and is_admin:
                        st.markdown("<div class='locked-warning'>🔒 เคสปิดงานแล้ว (ใส่รหัสแอดมินเพื่อแก้ไข)</div>", unsafe_allow_html=True)
                        c_pwd, c_btn = st.columns([3, 1])
                        with c_pwd: pwd_in = st.text_input("🔑 รหัสปลดล็อก", type="password", key="pwd_unlock")
                        with c_btn: 
                            if st.button("🔓 ปลดล็อก", use_container_width=True):
                                if pwd_in == "Patwit1510":
                                    st.session_state.unlock_password = "Patwit1510"
                                    st.rerun()
                                else: st.error("รหัสผิด")
                    
                    # Form แก้ไข
                    v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=is_locked)
                    v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=is_locked)
                    v_stmt = st.text_area("บันทึกผลการดำเนินการ *", value=clean_val(row.get('Statement')), disabled=is_locked)
                    
                    idx_stat = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                    v_sta = st.selectbox("สถานะ", STATUS_OPTIONS, index=idx_stat, disabled=is_locked)

                    if not is_locked:
                        if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                            df.at[idx, 'Victim'] = v_vic
                            df.at[idx, 'Accused'] = v_acc
                            df.at[idx, 'Statement'] = v_stmt
                            df.at[idx, 'Status'] = v_sta
                            
                            conn.update(data=df)
                            st.session_state.unlock_password = ""
                            st.cache_data.clear() # ล้างแคช
                            st.toast("✅ บันทึกเรียบร้อย!")
                            time.sleep(1); st.rerun()
                    
                    # --- [RESTORATION] ปุ่ม PDF ---
                    st.markdown("---")
                    st.write("#### 📄 เอกสาร")
                    has_stmt = clean_val(row.get('Statement')) != ""
                    pdf_data = create_pdf(row)
                    if isinstance(pdf_data, (bytes, bytearray)):
                        label = "🖨️ พิมพ์เอกสาร (PDF)" if has_stmt else "🖨️ พิมพ์แบบฟอร์มเปล่า"
                        btn_type = "primary" if has_stmt else "secondary"
                        st.download_button(label=label, data=bytes(pdf_data), file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True, type=btn_type)
                    else: st.error(f"❌ สร้าง PDF ไม่ได้: {pdf_data}")

    except Exception as e: st.error(f"Error: {e}")

# --- 6. หน้าหลักแจ้งเหตุ ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]); c2.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งความตำรวจนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"): st.session_state.submitted_id = None; st.rerun()
    else:
        with st.form("report"):
            rep = st.text_input("ชื่อผู้แจ้ง *")
            typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท", "สารเสพติด", "อาวุธ", "ลักทรัพย์", "บูลลี่", "อื่นๆ"])
            det = st.text_area("รายละเอียด *")
            
            if st.form_submit_button("ส่งข้อมูล", use_container_width=True):
                if rep and typ and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    df_old = conn.read(ttl="1m")
                    new_r = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid}])
                    conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                    
                    st.cache_data.clear() # ล้างแคช
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
