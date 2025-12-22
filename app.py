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
import qrcode
import xlsxwriter
import tempfile  # จำเป็นต้องใช้ตัวนี้เพื่อแก้ปัญหา PDF

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"
FONT_FILE = "THSarabunNew.ttf"

# รายชื่อสถานที่
LOCATION_OPTIONS = [
    "อาคาร 1", "อาคาร 2", "อาคาร 3", "อาคาร 4", "อาคาร 5",
    "หอประชุมเทาทอง", "หอประชุมไทรทอง", 
    "อาคารไฟฟ้าสนามฟุตบอล", "สนามบาส", "โรงอาหาร", "สนามปิงปอง",
    "สวนหลังห้องปกครอง", "สวนสนามเปตอง", "สวนเกษตร", "สวนหลังไทรทอง",
    "ห้องน้ำโรงอาหารติดอาคาร 4", "ห้องน้ำโรงอาหารติดประตูโรงอาหาร",
    "ห้องน้ำหลังอาคาร 3", "ห้องน้ำอาคารไฟฟ้า", "ห้องน้ำหลังอาคาร 5",
    "อื่นๆ"
]

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

# Data Privacy & Sanitization
def sanitize_input(text):
    if text:
        return str(text).replace("=", "").replace('"', "").replace("'", "").strip()
    return text

# ฟังก์ชันย่อรูปภาพ
def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((350, 350))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

# --- 2. Class PDF ---
class ReportPDF(FPDF):
    def header(self):
        if os.path.exists(FONT_FILE):
            self.add_font('ThaiFont', '', FONT_FILE)
            self.set_font('ThaiFont', '', 20)
        if os.path.exists(LOGO_FILE):
            self.image(LOGO_FILE, x=15, y=10, w=25)
        
        # Watermark
        self.set_font('ThaiFont', '', 40)
        self.set_text_color(240, 240, 240)
        self.set_xy(50, 100)
        self.cell(0, 0, txt="เอกสารลับ - Confidential", align='C')
        self.set_text_color(0, 0, 0)

        self.set_y(15)
        self.set_x(45)
        self.set_font('ThaiFont', '', 20)
        self.cell(0, 10, txt="สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", ln=True, align='L')
        self.set_font('ThaiFont', '', 16)
        self.set_x(45)
        self.cell(0, 10, txt="ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน", ln=True, align='L')
        self.ln(10)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        if os.path.exists(FONT_FILE):
            self.add_font('ThaiFont', '', FONT_FILE)
            self.set_font('ThaiFont', '', 10)
        
        printer = "System"
        if 'current_user' in st.session_state and st.session_state.current_user:
            printer = st.session_state.current_user['name']
        now_str = datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%d/%m/%Y %H:%M:%S")
        
        self.set_x(10)
        self.cell(0, 10, txt=f"พิมพ์โดย: {printer} | เวลา: {now_str} | หน้า {self.page_no()}", align='R')

# --- แก้ไขฟังก์ชัน create_pdf โดยใช้วิธี Temp File เพื่อแก้ปัญหา Encoding ---
def create_pdf(row_data):
    try:
        # 1. เช็กฟอนต์
        if not os.path.exists(FONT_FILE): 
            return b"ERROR: FONT_MISSING"

        # 2. สร้าง PDF Object
        pdf = ReportPDF()
        pdf.set_margins(20, 20, 20)
        pdf.add_page()
        epw = pdf.w - 2 * pdf.l_margin
        pdf.add_font('ThaiFont', '', FONT_FILE)
        pdf.set_font('ThaiFont', '', 14)
        
        # QR Code
        rid_text = clean_val(row_data.get('Report_ID'))
        qr = qrcode.make(rid_text)
        qr_buffer = io.BytesIO()
        qr.save(qr_buffer)
        qr_buffer.seek(0)
        pdf.image(qr_buffer, x=170, y=10, w=25, type='PNG')

        # ข้อมูลเบื้องต้น
        pdf.cell(epw*0.6, 8, txt=f"เลขที่รับแจ้ง: {rid_text}", ln=0)
        pdf.cell(epw*0.4, 8, txt=f"วันที่แจ้ง: {clean_val(row_data.get('Timestamp'))}", ln=1, align='R')
        pdf.ln(2)
        
        text_info = f"ผู้แจ้ง: {clean_val(row_data.get('Reporter'))}\n" \
                    f"ประเภทเหตุ: {clean_val(row_data.get('Incident_Type'))} | สถานที่: {clean_val(row_data.get('Location'))}"
        pdf.multi_cell(epw, 7, txt=text_info, border=0)
        pdf.ln(2)

        pdf.set_fill_color(245, 245, 245)
        pdf.multi_cell(epw, 7, txt=f"รายละเอียดเหตุการณ์:\n{clean_val(row_data.get('Details'))}", border=1, fill=True)
        pdf.ln(5)
        
        # ผลการสอบสวน
        pdf.set_font('ThaiFont', '', 16)
        pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14)
        
        statement_text = clean_val(row_data.get('Statement'))
        if not statement_text: statement_text = "-"
        pdf.multi_cell(epw, 7, txt=statement_text, border=1)
        
        # รูปหลักฐาน
        ev_img = clean_val(row_data.get('Evidence_Image'))
        if ev_img:
            pdf.ln(5)
            pdf.cell(0, 8, txt="หลักฐานประกอบ:", ln=True)
            try:
                img_data = base64.b64decode(ev_img)
                img_io = io.BytesIO(img_data)
                pdf.image(img_io, w=60)
            except: pass

        # ลายเซ็น
        pdf.ln(15)
        if pdf.get_y() > 220: pdf.add_page()
        col_w = epw / 2
        y1 = pdf.get_y()
        
        pdf.set_xy(20, y1); pdf.cell(col_w, 6, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_x(20); pdf.cell(col_w, 6, txt=f"( {clean_val(row_data.get('Victim'))} )", align='C', ln=1)
        pdf.set_x(20); pdf.cell(col_w, 6, txt="ผู้เสียหาย", align='C', ln=0)
        
        pdf.set_xy(20 + col_w, y1); pdf.cell(col_w, 6, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_x(20 + col_w); pdf.cell(col_w, 6, txt=f"( {clean_val(row_data.get('Accused'))} )", align='C', ln=1)
        pdf.set_x(20 + col_w); pdf.cell(col_w, 6, txt="ผู้ถูกกล่าวหา", align='C', ln=1)
        
        pdf.ln(12)
        y2 = pdf.get_y()
        
        pdf.set_xy(20, y2); pdf.cell(col_w, 6, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_x(20); pdf.cell(col_w, 6, txt=f"( {clean_val(row_data.get('Student_Police_Investigator'))} )", align='C', ln=1)
        pdf.set_x(20); pdf.cell(col_w, 6, txt="ตำรวจนักเรียนผู้สอบสวน", align='C', ln=0)
        
        pdf.set_xy(20 + col_w, y2); pdf.cell(col_w, 6, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.set_x(20 + col_w); pdf.cell(col_w, 6, txt=f"( {clean_val(row_data.get('Witness'))} )", align='C', ln=1)
        pdf.set_x(20 + col_w); pdf.cell(col_w, 6, txt="พยาน", align='C', ln=1)

        pdf.ln(15)
        pdf.cell(epw, 6, txt="ลงชื่อ..........................................................", align='C', ln=1)
        pdf.cell(epw, 6, txt=f"( {clean_val(row_data.get('Teacher_Investigator'))} )", align='C', ln=1)
        pdf.cell(epw, 6, txt="ครูผู้สอบสวน", align='C', ln=1)

        # === ส่วนที่แก้ไข: เขียนลงไฟล์ชั่วคราวแล้วอ่านกลับมาเป็น Bytes (แก้ปัญหา Encoding) ===
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)  # เขียนลงไฟล์จริง
            tmp_path = tmp_file.name
            
        with open(tmp_path, "rb") as f: # อ่านกลับด้วยโหมด Binary (rb)
            pdf_bytes = f.read()
            
        try:
            os.remove(tmp_path) # ลบไฟล์ทิ้งเมื่ออ่านเสร็จ
        except: pass
        
        return pdf_bytes # ส่งคืนค่า Bytes แท้ๆ

    except Exception as e:
        # ส่ง Error กลับเป็น Bytes เพื่อให้โค้ดปลายทางไม่ Error ซ้ำซ้อน
        return f"ERROR: {str(e)}".encode('utf-8')

# --- 3. Helper Functions ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

def clear_search_callback():
    st.session_state.search_query = ""

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    current_page = st.session_state[key]
    total_pages = math.ceil(total_items / limit)
    if total_pages == 0: total_pages = 1
    if current_page > total_pages: current_page = 1; st.session_state[key] = 1
    start_idx = (current_page - 1) * limit
    end_idx = start_idx + limit
    return start_idx, end_idx, current_page, total_pages

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", ""] or val is None: return ""
    return str(val).strip()

def render_case_list(df_subset, list_type):
    c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
    c1.markdown("**เลขที่รับแจ้ง**")
    c2.markdown("**วันเวลา**")
    c3.markdown("**ประเภทเหตุ**")
    c4.markdown("**สถานะ**")
    st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
    if df_subset.empty:
        st.caption("ไม่มีรายการในหน้านี้")
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

# --- 4. Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"<div class='main-header'>🏢 ระบบสอบสวน คุณ{user['name']}</div>", unsafe_allow_html=True)
    with col_h2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None; st.rerun()

    try:
        df = conn.read(ttl="1m")
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        if st.session_state.view_mode == "list":
            tab_list, tab_dash = st.tabs(["📋 รายการแจ้งเหตุ", "📊 แดชบอร์ดสถิติ"])
            
            with tab_list:
                c_search, c_btn_search, c_btn_clear = st.columns([3, 1, 1])
                with c_search:
                    search_q = st.text_input("ค้นหา", placeholder="เลขเคส, ชื่อ, หรือเหตุการณ์...", key="search_query", label_visibility="collapsed")
                with c_btn_search: st.button("🔍 ค้นหา", use_container_width=True)
                with c_btn_clear: st.button("❌ ล้าง", on_click=clear_search_callback, use_container_width=True)
                
                filtered_df = df.copy()
                if search_q:
                    filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                df_pending = filtered_df[filtered_df['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
                df_finished = filtered_df[filtered_df['Status'] == "ดำเนินการเรียบร้อย"][::-1]

                st.markdown("<h4 style='color:#1E3A8A; background-color:#f0f2f6; padding:10px; border-radius:5px;'>⏳ รายการที่รอการดำเนินการ</h4>", unsafe_allow_html=True)
                start_p, end_p, curr_p, tot_p = calculate_pagination('page_pending', len(df_pending), 5)
                render_case_list(df_pending.iloc[start_p:end_p], "pending")
                if tot_p > 1:
                    cp1, cp2, cp3 = st.columns([1, 2, 1])
                    with cp1: 
                        if st.button("⬅️ ย้อนกลับ (รอ)", key="btn_prev_pending", disabled=(curr_p==1)): 
                            st.session_state.page_pending -= 1; st.rerun()
                    with cp2: st.markdown(f"<div style='text-align:center; font-weight:bold; color:#555;'>หน้า {curr_p} / {tot_p}</div>", unsafe_allow_html=True)
                    with cp3: 
                        if st.button("ถัดไป (รอ) ➡️", key="btn_next_pending", disabled=(curr_p==tot_p)): 
                            st.session_state.page_pending += 1; st.rerun()

                st.markdown("---")
                st.markdown("<h4 style='color:#2e7d32; background-color:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                start_f, end_f, curr_f, tot_f = calculate_pagination('page_finished', len(df_finished), 5)
                render_case_list(df_finished.iloc[start_f:end_f], "finished")
                if tot_f > 1:
                    cf1, cf2, cf3 = st.columns([1, 2, 1])
                    with cf1: 
                        if st.button("⬅️ ย้อนกลับ (เสร็จ)", key="btn_prev_finished", disabled=(curr_f==1)): 
                            st.session_state.page_finished -= 1; st.rerun()
                    with cf2: st.markdown(f"<div style='text-align:center; font-weight:bold; color:#555;'>หน้า {curr_f} / {tot_f}</div>", unsafe_allow_html=True)
                    with cf3: 
                        if st.button("ถัดไป (เสร็จ) ➡️", key="btn_next_finished", disabled=(curr_f==tot_f)): 
                            st.session_state.page_finished += 1; st.rerun()

            with tab_dash:
                st.subheader("📊 สรุปสถิติ")
                with st.expander("📥 Export ข้อมูล"):
                    if not df.empty:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='ReportData')
                        st.download_button(label="ดาวน์โหลดไฟล์ Excel", data=buffer, file_name=f"Report_Export_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.ms-excel")
                
                if not df.empty:
                    total_cases = len(df)
                    top_loc = df['Location'].mode()[0] if not df['Location'].mode().empty else "-"
                    top_inc = df['Incident_Type'].mode()[0] if not df['Incident_Type'].mode().empty else "-"
                    m1, m2, m3 = st.columns(3)
                    m1.metric("แจ้งเหตุทั้งหมด", f"{total_cases} ครั้ง")
                    m2.metric("สถานที่เกิดเหตุบ่อยสุด", top_loc)
                    m3.metric("เหตุที่เกิดบ่อยสุด", top_inc)

                    st.markdown("---")
                    c_text1, c_text2 = st.columns(2)
                    with c_text1:
                        st.markdown("**📌 สรุปยอดตามสถานที่ (Top 5)**")
                        loc_counts = df['Location'].value_counts().head(5)
                        for loc, count in loc_counts.items():
                            percent = (count / total_cases) * 100
                            st.markdown(f"- **{loc}**: {count} ครั้ง <span style='color:red; font-size:0.8em;'>({percent:.1f}%)</span>", unsafe_allow_html=True)
                    with c_text2:
                        st.markdown("**📌 สรุปยอดตามประเภทเหตุ**")
                        type_counts = df['Incident_Type'].value_counts()
                        for inc, count in type_counts.items():
                            percent = (count / total_cases) * 100
                            st.markdown(f"- **{inc}**: {count} ครั้ง <span style='color:red; font-size:0.8em;'>({percent:.1f}%)</span>", unsafe_allow_html=True)

                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🔹 แผนภูมิวงกลม: สัดส่วนประเภทเหตุ**")
                        st.bar_chart(type_counts, color="#FF4B4B")
                    with col2:
                        st.markdown("**🔹 กราฟแท่ง: สถิติสถานที่เกิดเหตุ**")
                        st.bar_chart(df['Location'].value_counts(), color="#1E3A8A")
                    
                    st.markdown("---")
                    st.subheader("📈 สถิติเชิงลึก (Advanced Analytics)")
                    df['datetime'] = pd.to_datetime(df['Timestamp'], format="%d/%m/%Y %H:%M:%S", errors='coerce')
                    df = df.dropna(subset=['datetime'])
                    df['Hour'] = df['datetime'].dt.hour
                    df['Day'] = df['datetime'].dt.strftime('%A')
                    days_th = {'Monday': 'จันทร์', 'Tuesday': 'อังคาร', 'Wednesday': 'พุธ', 'Thursday': 'พฤหัสบดี', 'Friday': 'ศุกร์', 'Saturday': 'เสาร์', 'Sunday': 'อาทิตย์'}
                    df['DayTH'] = df['Day'].map(days_th)

                    adv1, adv2 = st.columns(2)
                    with adv1:
                        st.markdown("**🔥 ความสัมพันธ์: สถานที่ vs ประเภทเหตุ**")
                        corr_df = pd.crosstab(df['Location'], df['Incident_Type'])
                        st.dataframe(corr_df.style.background_gradient(cmap="Reds"), use_container_width=True, height=300)
                    with adv2:
                        st.markdown("**🕒 ช่วงเวลาเกิดเหตุ (Heatmap Analysis)**")
                        heatmap_df = pd.crosstab(df['DayTH'], df['Hour'])
                        st.dataframe(heatmap_df.style.background_gradient(cmap="Blues"), use_container_width=True, height=300)
                else: st.info("ยังไม่มีข้อมูลในระบบ")

        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            sel = df[df['Report_ID'] == sid]
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list)
                
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
                        st.markdown("<div style='color:red;'>🔒 เคสนี้ดำเนินการเรียบร้อยแล้ว (ใช้รหัสเจ้าหน้าที่ระดับสูงสุด)</div>", unsafe_allow_html=True)
                        cpwd, cbtn = st.columns([3, 1])
                        pwd_in = cpwd.text_input("รหัสปลดล็อค", type="password")
                        if cbtn.button("ปลดล็อค"):
                            if pwd_in == "Patwit1510": st.session_state.unlock_password = "Patwit1510"; st.rerun()

                    c1, c2 = st.columns(2)
                    with c1:
                        v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=is_locked)
                        v_wit = st.text_input("พยาน", value=clean_val(row.get('Witness')), disabled=is_locked)
                        v_stu = st.text_input("ตำรวจนักเรียนผู้สอบสวน *", value=clean_val(row.get('Student_Police_Investigator')), disabled=is_locked)
                    with c2:
                        v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=is_locked)
                        v_tea = st.text_input("ครูผู้สอบสวน *", value=clean_val(row.get('Teacher_Investigator')), disabled=is_locked)
                    
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
                            df.at[idx, 'Witness'] = v_wit
                            df.at[idx, 'Teacher_Investigator'] = v_tea
                            df.at[idx, 'Student_Police_Investigator'] = v_stu
                            df.at[idx, 'Statement'] = v_stmt
                            df.at[idx, 'Status'] = v_sta
                            df.at[idx, 'Evidence_Image'] = final_img
                            df.at[idx, 'Audit_Log'] = f"{old_log}\n{new_log}" if old_log else new_log
                            conn.update(data=df)
                            st.cache_data.clear()
                            st.success("บันทึกเรียบร้อย!"); time.sleep(1); st.rerun()

                    # --- เมนู PDF แยกต่างหาก ---
                    st.markdown("---")
                    with st.container(border=True):
                        st.markdown("#### 🖨️ เมนูพิมพ์รายงาน")
                        col_pdf_1, col_pdf_2 = st.columns([3, 1])
                        with col_pdf_1:
                            st.caption("ดาวน์โหลดรายงานสรุปผลการสอบสวนในรูปแบบ PDF (ประกอบด้วยข้อมูลผู้แจ้ง, รายละเอียด, และผลการสอบสวน)")
                        with col_pdf_2:
                            pdf_bytes = create_pdf(row)
                            
                            # ตรวจสอบว่าเป็น Error Message แบบ Bytes หรือไม่
                            if pdf_bytes.startswith(b"ERROR"):
                                st.error(f"ระบบ PDF ขัดข้อง: {pdf_bytes.decode('utf-8', errors='ignore')}")
                            else:
                                st.download_button(
                                    label="ดาวน์โหลด PDF",
                                    data=pdf_bytes,
                                    file_name=f"Report_{sid}.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True
                                )
                    
                    with st.expander("📜 ดูประวัติการแก้ไข (Audit Trail)"):
                        st.text(row.get('Audit_Log', 'ไม่มีประวัติ'))

    except Exception as e: st.error(f"Error: {e}")

# --- 5. หน้าหลักสำหรับนักเรียน ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]); c2.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 แจ้งเหตุใหม่", "🔍 ติดตามสถานะ"])
    
    with tab1:
        with st.form("report_form"):
            rep = sanitize_input(st.text_input("ชื่อผู้แจ้ง *"))
            typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สารเสพติด", "อาวุธ", "ลักทรัพย์", "บูลลี่", "อื่นๆ"])
            loc = st.selectbox("สถานที่เกิดเหตุ *", LOCATION_OPTIONS)
            det = sanitize_input(st.text_area("รายละเอียดเหตุการณ์ *"))
            img = st.file_uploader("แนบรูปภาพประกอบ (ถ้ามี)", type=['jpg','png'])
            
            st.markdown("---")
            pdpa_check = st.checkbox("ข้าพเจ้ายินยอมให้เก็บรวบรวมข้อมูลเพื่อใช้ในการดำเนินงานของสถานีตำรวจนักเรียนและข้อมูลท่านจะไม่ถูกเปิดเผยต่อคู่กรณี")
            st.markdown("""
                <div style='background-color: #ffebee; padding: 10px; border-radius: 5px; border-left: 5px solid #ef5350;'>
                    <span style='color: #c62828; font-weight: bold;'>⚠️ คำเตือน:</span> การแจ้งความเท็จเพื่อกลั่นแกล้งผู้อื่นมีความผิดตามกฎหมายอาญา<br>
                    <span style='color: #c62828; font-size: 0.9em;'>* การแจ้งเหตุนี้ไม่ใช่การแจ้งความที่มีผลเท่าการแจ้งความต่อเจ้าหน้าที่ตำรวจตามกฎหมายอาญา</span>
                </div>
            """, unsafe_allow_html=True)
            
            if st.form_submit_button("ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
                if not pdpa_check:
                    st.warning("⚠️ กรุณากดยินยอม PDPA ก่อนส่งข้อมูล")
                elif rep and loc and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    df_old = conn.read(ttl="1m")
                    new_data = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": process_image(img)}])
                    conn.update(data=pd.concat([df_old, new_data], ignore_index=True))
                    st.cache_data.clear()
                    st.success(f"ส่งข้อมูลสำเร็จ! รหัสรับแจ้งคือ: {rid}")
                    st.info("⚠️ กรุณาจดจำเลข 4 ตัวท้ายของรหัสรับแจ้ง เพื่อใช้ตรวจสอบสถานะ")
                else: st.error("กรุณากรอกข้อมูลให้ครบ")

    with tab2:
        st.subheader("🔍 ตรวจสอบสถานะการดำเนินงาน")
        st.markdown("กรอก **เลข 4 ตัวท้าย** ของรหัสรับแจ้ง (เช่น 5929) เพื่อตรวจสอบสถานะ")
        search_code = sanitize_input(st.text_input("เลข 4 ตัวท้าย", max_chars=4, placeholder="ตัวอย่าง: 5929"))
        
        if st.button("🔎 ค้นหา", use_container_width=True):
            if len(search_code) == 4 and search_code.isdigit():
                try:
                    df = conn.read(ttl="1m")
                    df = df.fillna("")
                    df['Report_ID'] = df['Report_ID'].astype(str)
                    match = df[df['Report_ID'].str.endswith(search_code)]
                    
                    if not match.empty:
                        for idx, row in match.iterrows():
                            with st.container(border=True):
                                st.markdown(f"#### 📌 เลขที่รับแจ้ง: {row['Report_ID']}")
                                c1, c2 = st.columns(2)
                                c1.write(f"**ประเภทเหตุ:** {row['Incident_Type']}")
                                status = row['Status']
                                color = "orange"
                                if status == "ดำเนินการเรียบร้อย": color = "green"
                                elif status == "อยู่ระหว่างการดำเนินการ": color = "blue"
                                elif status == "ยกเลิก": color = "red"
                                c2.markdown(f"**สถานะ:** <span style='color:{color};font-weight:bold'>{status}</span>", unsafe_allow_html=True)
                                st.caption(f"อัปเดตล่าสุด: {row.get('Timestamp')}")
                    else: st.warning(f"ไม่พบข้อมูลของเลขท้าย {search_code}")
                except Exception as e: st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
            else: st.error("กรุณากรอกตัวเลขให้ครบ 4 หลัก")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            accounts = st.secrets.get("officer_accounts", {})
            if pw in accounts:
                st.session_state.current_user = accounts[pw]
                st.rerun()
            else: st.error("รหัสผิด")

# --- Run ---
st.markdown("<style>.main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }</style>", unsafe_allow_html=True)
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

if st.session_state.current_user: officer_dashboard()
else: main_page()
