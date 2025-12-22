import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import random
import os
import base64
import io
import qrcode
import glob
import math
import mimetypes
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from PIL import Image

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", page_icon="👮‍♂️", layout="wide")

# --- ค้นหาไฟล์ (Font & Logo) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# ฟังก์ชันแปลงรูปภาพเป็น Base64
def get_base64_image(image_path):
    if not image_path or not os.path.exists(image_path):
        return ""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        return ""

# --- ระบบค้นหาโลโก้ ---
LOGO_PATH = None
LOGO_MIME = "image/png" 

target_file = os.path.join(BASE_DIR, "school_logo")
if os.path.exists(target_file):
    LOGO_PATH = target_file
    try:
        with Image.open(target_file) as img:
            if img.format == 'JPEG': LOGO_MIME = "image/jpeg"
            elif img.format == 'PNG': LOGO_MIME = "image/png"
    except: pass
else:
    possible_logos = glob.glob(os.path.join(BASE_DIR, "school_logo*"))
    for f in possible_logos:
        if os.path.isfile(f):
            LOGO_PATH = f
            try:
                with Image.open(f) as img:
                    if img.format == 'JPEG': LOGO_MIME = "image/jpeg"
                    elif img.format == 'PNG': LOGO_MIME = "image/png"
            except: pass
            break

LOGO_BASE64 = get_base64_image(LOGO_PATH) if LOGO_PATH else ""

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

def sanitize_input(text):
    if text:
        return str(text).replace("=", "").replace('"', "").replace("'", "").strip()
    return text

def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        img.thumbnail((800, 800))
        buffer = io.BytesIO()
        
        img.save(buffer, format="JPEG", quality=65, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

# --- [SAFETY FIX] ฟังก์ชันตรวจสอบคอลัมน์แบบปลอดภัย (ไม่ลบข้อมูล) ---
def safe_ensure_columns(df):
    required_cols = [
        'Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 
        'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 
        'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 
        'Statement', 'Evidence_Image'
    ]
    
    # ถ้า DataFrame ว่างจริง (ไม่มีแถวและไม่มีคอลัมน์) ค่อยสร้าง Header ใหม่
    if df is None:
        return pd.DataFrame(columns=required_cols)
        
    # แก้ชื่อคอลัมน์ที่มีช่องว่าง
    df.columns = df.columns.str.strip()
    
    # เติมเฉพาะคอลัมน์ที่ขาด (ไม่แตะต้องข้อมูลที่มีอยู่)
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
            
    return df

# --- รายชื่อสถานที่ ---
LOCATION_OPTIONS = [
    "อาคาร 1", "อาคาร 2", "อาคาร 3", "อาคาร 4", "อาคาร 5",
    "หอประชุมเทาทอง", "หอประชุมไทรทอง", 
    "อาคารไฟฟ้าสนามฟุตบอล", "สนามบาส", "โรงอาหาร", "สนามปิงปอง",
    "สวนหลังห้องปกครอง", "สวนสนามเปตอง", "สวนเกษตร", "สวนหลังไทรทอง",
    "ห้องน้ำโรงอาหารติดอาคาร 4", "ห้องน้ำโรงอาหารติดประตูโรงอาหาร",
    "ห้องน้ำหลังอาคาร 3", "ห้องน้ำอาคารไฟฟ้า", "ห้องน้ำหลังอาคาร 5",
    "อื่นๆ"
]

# --- ฟังก์ชันสร้าง PDF (WeasyPrint) ---
def create_pdf(row):
    rid = str(row.get('Report_ID', ''))
    date_str = str(row.get('Timestamp', ''))
    reporter = str(row.get('Reporter', '-'))
    incident = str(row.get('Incident_Type', '-'))
    location = str(row.get('Location', '-'))
    details = str(row.get('Details', '-'))
    statement = str(row.get('Statement', '-'))
    
    audit_log = str(row.get('Audit_Log', ''))
    latest_date = "-"
    if audit_log:
        try:
            lines = [line for line in audit_log.split('\n') if line.strip()]
            if lines:
                last_line = lines[-1]
                if '[' in last_line and ']' in last_line:
                    latest_date = last_line[last_line.find('[')+1 : last_line.find(']')]
        except: pass

    printer_name = st.session_state.current_user['name'] if st.session_state.current_user else "System"
    print_time = datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%d/%m/%Y %H:%M:%S")

    qr = qrcode.make(rid)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

    evidence_html = ""
    if row.get('Evidence_Image'):
        evidence_html = f"""
        <div style='margin-top: 10px; page-break-inside: avoid;'>
            <b>หลักฐานประกอบ:</b><br>
            <img src="data:image/jpeg;base64,{row.get('Evidence_Image')}" style="max-height: 150px; border: 1px solid #ccc;">
        </div>
        """

    logo_html = ""
    if LOGO_BASE64:
        logo_html = f'<img class="logo" src="data:{LOGO_MIME};base64,{LOGO_BASE64}">'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @font-face {{
                font-family: 'THSarabunNew';
                src: url('file://{FONT_FILE}');
            }}
            @page {{
                size: A4;
                margin: 2cm;
                @bottom-right {{
                    content: "ผู้พิมพ์: {printer_name} | เวลา: {print_time} | หน้า " counter(page);
                    font-family: 'THSarabunNew';
                    font-size: 12pt;
                }}
            }}
            body {{
                font-family: 'THSarabunNew';
                font-size: 16pt;
                line-height: 1.3;
            }}
            .header {{
                text-align: center;
                position: relative;
                margin-bottom: 20px;
                min-height: 80px;
            }}
            .logo {{
                position: absolute;
                top: 0;
                left: 0;
                width: 60px;
                height: auto;
            }}
            .qr {{
                position: absolute;
                top: 0;
                right: 0;
                width: 60px;
            }}
            .title {{
                font-size: 22pt;
                font-weight: bold;
                margin-top: 10px;
                margin-left: 70px; 
                margin-right: 70px;
            }}
            .subtitle {{
                font-size: 18pt;
                font-weight: bold;
                margin-left: 70px;
                margin-right: 70px;
            }}
            .info-table {{
                width: 100%;
                margin-bottom: 10px;
                border-collapse: collapse;
            }}
            .box {{
                border: 1px solid #000;
                background-color: #f9f9f9;
                padding: 10px;
                margin-bottom: 10px;
                min-height: 50px;
                white-space: pre-wrap; 
            }}
            .signature-table {{
                width: 100%;
                margin-top: 30px;
                text-align: center;
                page-break-inside: avoid;
            }}
            .signature-table td {{
                padding-bottom: 30px;
                vertical-align: top;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            {logo_html}
            <div class="title">สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</div>
            <div class="subtitle">ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน</div>
            <img class="qr" src="data:image/png;base64,{qr_base64}">
        </div>
        <hr>
        <table class="info-table">
            <tr>
                <td width="60%"><b>เลขที่รับแจ้ง:</b> {rid}</td>
                <td width="40%" style="text-align:right;">
                    <b>วันที่แจ้ง:</b> {date_str}<br>
                    <span style="font-size: 14pt;"><b>วันที่บันทึกผล:</b> {latest_date}</span>
                </td>
            </tr>
            <tr>
                <td colspan="2"><b>ผู้แจ้ง:</b> {reporter}</td>
            </tr>
            <tr>
                <td><b>ประเภทเหตุ:</b> {incident}</td>
                <td><b>สถานที่:</b> {location}</td>
            </tr>
        </table>
        
        <div style="margin-top:10px;"><b>รายละเอียดเหตุการณ์:</b></div>
        <div class="box">{details}</div>
        
        <div><b>ผลการดำเนินการสอบสวน:</b></div>
        <div class="box">{statement}</div>
        
        {evidence_html}
        
        <table class="signature-table">
            <tr>
                <td width="50%">
                    ลงชื่อ..........................................................<br>
                    ( {row.get('Victim', '')} )<br>ผู้เสียหาย
                </td>
                <td width="50%">
                    ลงชื่อ..........................................................<br>
                    ( {row.get('Accused', '')} )<br>ผู้ถูกกล่าวหา
                </td>
            </tr>
            <tr>
                <td>
                    ลงชื่อ..........................................................<br>
                    ( {row.get('Student_Police_Investigator', '')} )<br>ตำรวจนักเรียนผู้สอบสวน
                </td>
                <td>
                    ลงชื่อ..........................................................<br>
                    ( {row.get('Witness', '')} )<br>พยาน
                </td>
            </tr>
            <tr>
                <td colspan="2">
                    <br>
                    ลงชื่อ..........................................................<br>
                    ( {row.get('Teacher_Investigator', '')} )<br>ครูผู้สอบสวน
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    font_config = FontConfiguration()
    pdf_bytes = HTML(string=html_content, base_url=BASE_DIR).write_pdf(font_config=font_config)
    return pdf_bytes

# --- Helper Functions ---
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", ""] or val is None: return ""
    return str(val).strip()

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    current_page = st.session_state[key]
    total_pages = math.ceil(total_items / limit)
    if total_pages == 0: total_pages = 1
    if current_page > total_pages: current_page = 1; st.session_state[key] = 1
    start_idx = (current_page - 1) * limit
    end_idx = start_idx + limit
    return start_idx, end_idx, current_page, total_pages

# --- Callbacks ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

def clear_search_callback():
    st.session_state.search_query = ""

# --- 4. Dashboard (เจ้าหน้าที่) ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
    with col_h1:
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            try: st.image(LOGO_PATH, width=80)
            except: st.write("Logo Error")
    with col_h2:
        st.markdown(f"<div style='font-size: 26px; font-weight: bold; color: #1E3A8A; padding-top: 20px;'>🏢 ระบบสอบสวน คุณ{user['name']}</div>", unsafe_allow_html=True)
    with col_h3: 
        st.write("") 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None; st.rerun()

    try:
        # [CRITICAL FIX] บังคับอ่านข้อมูลสด + ซ่อมคอลัมน์ ก่อนค้นหา
        df = conn.read(ttl="0")
        df = safe_ensure_columns(df)
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

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
                
                c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
                c1.markdown("**เลขที่รับแจ้ง**"); c2.markdown("**วันเวลา**"); c3.markdown("**ประเภทเหตุ**"); c4.markdown("**สถานะ**")
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                
                if df_pending.empty: st.caption("ไม่มีรายการ")
                for index, row in df_pending.iloc[start_p:end_p].iterrows():
                    raw_rid = str(row.get('Report_ID', '')).strip()
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: 
                        st.button(f"📝 {raw_rid}", key=f"p_{index}", use_container_width=True, on_click=view_case, args=(raw_rid,))
                    with cc2: st.write(row.get('Timestamp', '-'))
                    with cc3: st.write(row.get('Incident_Type', '-'))
                    with cc4: st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ รอสอบสวน</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)
                
                if tot_p > 1:
                    cp1, cp2, cp3 = st.columns([1, 2, 1])
                    with cp1: 
                        if st.button("⬅️ ย้อนกลับ (รอ)", key="prev_p", disabled=(curr_p==1)): st.session_state.page_pending -= 1; st.rerun()
                    with cp2: st.markdown(f"<div style='text-align:center;'>หน้า {curr_p} / {tot_p}</div>", unsafe_allow_html=True)
                    with cp3: 
                        if st.button("ถัดไป (รอ) ➡️", key="next_p", disabled=(curr_p==tot_p)): st.session_state.page_pending += 1; st.rerun()

                st.markdown("---")
                st.markdown("<h4 style='color:#2e7d32; background-color:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                start_f, end_f, curr_f, tot_f = calculate_pagination('page_finished', len(df_finished), 5)
                
                c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
                c1.markdown("**เลขที่รับแจ้ง**"); c2.markdown("**วันเวลา**"); c3.markdown("**ประเภทเหตุ**"); c4.markdown("**สถานะ**")
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                
                if df_finished.empty: st.caption("ไม่มีรายการ")
                for index, row in df_finished.iloc[start_f:end_f].iterrows():
                    raw_rid = str(row.get('Report_ID', '')).strip()
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: 
                        st.button(f"✅ {raw_rid}", key=f"f_{index}", use_container_width=True, on_click=view_case, args=(raw_rid,))
                    with cc2: st.write(row.get('Timestamp', '-'))
                    with cc3: st.write(row.get('Incident_Type', '-'))
                    with cc4: st.markdown(f"<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

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
                        type_counts = df['Incident_Type'].value_counts().head(5)
                        for inc, count in type_counts.items():
                            percent = (count / total_cases) * 100
                            st.markdown(f"- **{inc}**: {count} ครั้ง <span style='color:red; font-size:0.8em;'>({percent:.1f}%)</span>", unsafe_allow_html=True)

                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🔹 แผนภูมิวงกลม: สัดส่วนประเภทเหตุ**")
                        st.bar_chart(df['Incident_Type'].value_counts(), color="#FF4B4B")
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
                        st.dataframe(corr_df, use_container_width=True, height=300)
                    with adv2:
                        st.markdown("**🕒 ช่วงเวลาเกิดเหตุ (Heatmap Analysis)**")
                        heatmap_df = pd.crosstab(df['DayTH'], df['Hour'])
                        st.dataframe(heatmap_df, use_container_width=True, height=300)

        elif st.session_state.view_mode == "detail":
            st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list, use_container_width=True)
            
            sid = str(st.session_state.selected_case_id).strip()
            sel = df[df['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                
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
                        v_stu = st.text_input("ตำรวจนักเรียน *", value=clean_val(row.get('Student_Police_Investigator')), disabled=is_locked)
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

                    # --- ปุ่ม PDF ---
                    st.markdown("---")
                    with st.container(border=True):
                        st.markdown("#### 🖨️ เมนูพิมพ์รายงาน")
                        col_pdf_1, col_pdf_2 = st.columns([3, 1])
                        with col_pdf_1:
                            st.caption("ดาวน์โหลดรายงานสรุปผลการสอบสวนในรูปแบบ PDF (ประกอบด้วยข้อมูลผู้แจ้ง, รายละเอียด, และผลการสอบสวน)")
                        with col_pdf_2:
                            try:
                                pdf_bytes = create_pdf(row)
                                st.download_button(
                                    label="ดาวน์โหลด PDF",
                                    data=pdf_bytes,
                                    file_name=f"Report_{sid}.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")
                                if "pango" in str(e).lower():
                                    st.error("⚠️ กรุณาตรวจสอบว่าไฟล์ packages.txt มีคำว่า 'pango' แล้ว")
                    
                    with st.expander("📜 ดูประวัติการแก้ไข (Audit Trail)"):
                        st.text(row.get('Audit_Log', 'ไม่มีประวัติ'))
            else:
                st.error(f"ไม่พบข้อมูลของเลขที่รับแจ้ง: {sid}")

    except Exception as e: st.error(f"Error: {e}")

    # Debug Menu
    st.markdown("---")
    if user.get('role') == 'admin':
        with st.expander("🛠️ สำหรับผู้ดูแลระบบ (ตรวจสอบไฟล์)"):
            admin_pwd = st.text_input("กรุณาใส่รหัส Admin เพื่อเข้าถึงข้อมูล:", type="password", key="debug_admin_pwd")
            if admin_pwd == "Patwit1510":
                st.success("Access Granted")
                st.write(f"📂 โฟลเดอร์ปัจจุบัน: `{BASE_DIR}`")
                st.write(f"📄 ไฟล์ฟอนต์: `{FONT_FILE}` ({'✅ พบ' if os.path.exists(FONT_FILE) else '❌ ไม่พบ'})")
                found_logos = glob.glob(os.path.join(BASE_DIR, "school_logo*"))
                st.write(f"🖼️ ไฟล์รูปโลโก้ที่พบ ({len(found_logos)} ไฟล์):")
                if found_logos:
                    for f in found_logos: st.code(os.path.basename(f))
                else: st.error("❌ ไม่พบไฟล์ที่ชื่อขึ้นต้นด้วย school_logo")
                st.write("---")
                st.write(f"✅ ไฟล์โลโก้ที่ระบบเลือกใช้: `{os.path.basename(LOGO_PATH) if LOGO_PATH else 'ไม่มี'}`")
                st.write(f"✅ MIME Type ที่ใช้ใน PDF: `{LOGO_MIME}`")
            elif admin_pwd:
                st.error("รหัสผ่านไม่ถูกต้อง")

# --- 5. หน้าหลักสำหรับนักเรียน ---
def main_page():
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        c1, c2, c3 = st.columns([5, 1, 5])
        c2.image(LOGO_PATH, width=100)
    
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 แจ้งเหตุใหม่", "🔍 ติดตามสถานะ"])
    
    with tab1:
        with st.form("report_form"):
            rep = sanitize_input(st.text_input("ชื่อผู้แจ้ง *"))
            typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท/ทำร้ายร่างกาย", "สารเสพติด/บุหรี่ไฟฟ้า/แอลกอฮอ", "พกอาวุธ", "ลักทรัพย์/ทำลายทรัพย์สิน", "ข่มขู่/บูลลี่/ด่าทอบนออนไลน์", "ล่วงละเมิดทางเพศ", "อื่นๆ"])
            loc = st.selectbox("สถานที่เกิดเหตุ *", LOCATION_OPTIONS)
            # [UPDATE] เพิ่ม Placeholder ตรงนี้
            det = sanitize_input(st.text_area("รายละเอียดเหตุการณ์ *", placeholder="ตัวอย่างการกรอก เกิดเหตุอะไร ที่ใด ใครเป็นคนกระทำความผิด(ถ้าทราบ)"))
            img = st.file_uploader("แนบรูปภาพประกอบ (ถ้ามี)", type=['jpg','png'])
            
            st.markdown("---")
            pdpa_check = st.checkbox("ข้าพเจ้ายินยอมให้เก็บรวบรวมข้อมูลเพื่อใช้ในการดำเนินงานของสถานีตำรวจนักเรียนและข้อมูลท่านจะไม่ถูกเปิดเผยต่อคู่กรณี")
            st.markdown("""
                <div style='background-color: #ffebee; padding: 10px; border-radius: 5px; border-left: 5px solid #ef5350;'>
                    <span style='color: #c62828; font-weight: bold;'>⚠️ คำเตือน:</span> การแจ้งความเท็จเพื่อกลั่นแกล้งผู้อื่นมีความผิดตามกฎหมายอาญา<br>
                    <span style='color: #c62828; font-size: 0.9em;'>* การแจ้งเหตุนี้ไม่ใช่การแจ้งความที่มีผลเท่าการแจ้งความต่อเจ้าหน้าที่ตำรวจตามกฎหมายอาญา</span>
                </div>
            """, unsafe_allow_html=True)
            
            submitted = st.form_submit_button("ส่งข้อมูลแจ้งเหตุ", use_container_width=True)
            
            if submitted:
                if 'last_submit_time' in st.session_state:
                    time_diff = (datetime.now() - st.session_state.last_submit_time).total_seconds()
                    if time_diff < 60:
                        st.error(f"⚠️ กรุณารออีก {60 - int(time_diff)} วินาที ก่อนแจ้งเหตุครั้งต่อไป")
                        st.stop()

                if len(det) < 10:
                    st.error("⚠️ กรุณาระบุรายละเอียดเหตุการณ์ให้ชัดเจนกว่านี้ (อย่างน้อย 10 ตัวอักษร)")
                
                elif not pdpa_check:
                    st.warning("⚠️ กรุณากดยินยอม PDPA ก่อนส่งข้อมูล")
                elif rep and loc and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    # --- [CRITICAL FIX] บังคับอ่านข้อมูลสด + ซ่อมคอลัมน์ ก่อนบันทึก ---
                    df_old = conn.read(ttl="0") 
                    df_old = safe_ensure_columns(df_old)
                    # ----------------------------------------------------------------
                    new_data = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": process_image(img)}])
                    
                    for c in df_old.columns:
                        if c not in new_data.columns: new_data[c] = ""
                        
                    conn.update(data=pd.concat([df_old, new_data], ignore_index=True))
                    st.cache_data.clear()
                    
                    st.session_state.last_submit_time = datetime.now()
                    
                    st.success(f"ส่งข้อมูลสำเร็จ! รหัสรับแจ้งคือ: {rid}")
                    st.info("⚠️ กรุณาจดจำเลข 4 ตัวท้ายของรหัสรับแจ้ง เพื่อใช้ตรวจสอบสถานะ")
                else: 
                    st.error("กรุณากรอกข้อมูลให้ครบ")

    with tab2:
        st.subheader("🔍 ตรวจสอบสถานะการดำเนินงาน")
        st.markdown("กรอก **เลข 4 ตัวท้าย** ของรหัสรับแจ้ง (เช่น 5929) เพื่อตรวจสอบสถานะ")
        search_code = sanitize_input(st.text_input("เลข 4 ตัวท้าย", max_chars=4, placeholder="ตัวอย่าง: 5929"))
        
        if st.button("🔎 ค้นหา", use_container_width=True):
            if len(search_code) == 4 and search_code.isdigit():
                try:
                    # --- [CRITICAL FIX] บังคับอ่านข้อมูลสด + ซ่อมคอลัมน์ ก่อนค้นหา ---
                    df = conn.read(ttl="0")
                    df = safe_ensure_columns(df)
                    # ----------------------------------------------------------------
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
    st.info("กรุณาเข้าสู่ระบบเพื่อใช้งานสำหรับเจ้าหน้าที่")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            accounts = st.secrets.get("officer_accounts", {})
            if pw in accounts:
                st.session_state.current_user = accounts[pw]
                st.rerun()
            else: st.error("รหัสผิด")

# --- Run ---
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

if st.session_state.current_user: officer_dashboard()
else: main_page()
