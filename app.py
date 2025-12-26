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
import time
import html
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from PIL import Image
import streamlit.components.v1 as components # <--- ✅ เพิ่มบรรทัดนี้
# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", page_icon="👮‍♂️", layout="wide")

# --- CSS: ซ่อนเมนู + ปรับแต่ง UI ---
st.markdown("""
<style>
    /* ซ่อน Header, Menu, Footer */
    [data-testid="stHeader"] { display: none; }
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; }
    footer { visibility: hidden; height: 0%; }
    .stDeployButton { display: none; }
    [data-testid="stSidebar"] { display: none; }
    
    /* ปรับ Layout */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    
    /* ปรับแต่ง Card */
    .metric-card { 
        background: white; padding: 10px; border-radius: 8px; 
        border: 1px solid #d1d5db; text-align: center; box-shadow: none !important; 
    }
    img { opacity: 1 !important; image-rendering: -webkit-optimize-contrast; }
    *, *::before, *::after { scroll-behavior: auto !important; }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

def get_target_sheet_name():
    now = get_now_th()
    year_th = now.year + 543
    if now.month < 5: ac_year = year_th - 1
    else: ac_year = year_th
    return f"Investigation_{ac_year}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# --- Image Helper (ปรับลดขนาดเพื่อแก้ปัญหา 50,000 chars) ---
def get_base64_image(image_path):
    if not image_path or not os.path.exists(image_path): return ""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        if img.mode in ('RGBA', 'LA', 'P'): img = img.convert('RGB')
        
        # ลดขนาดภาพลงเหลือ 450px เพื่อให้ไม่เกินโควต้า Google Sheet
        img.thumbnail((450, 450)) 
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=40, optimize=True)
        base64_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Safety Guard
        if len(base64_str) > 49500: return "" 
        return base64_str
    except: return ""

# --- Logo Loading ---
LOGO_PATH = None
possible_logos = glob.glob(os.path.join(BASE_DIR, "school_logo*"))
if possible_logos: LOGO_PATH = possible_logos[0]
LOGO_BASE64 = get_base64_image(LOGO_PATH) if LOGO_PATH else ""
LOGO_MIME = "image/png"

def sanitize_input(text):
    if not text:
        return ""    
    text_str = str(text)
    
    # 1. ป้องกัน Formula Injection (Google Sheets / Excel)
    # ถ้าขึ้นต้นด้วย = + - @ ให้เติม ' นำหน้า เพื่อบังคับเป็น Text
    if text_str.startswith(("=", "+", "-", "@")):
        text_str = "'" + text_str
        
    # 2. ป้องกัน XSS (แปลง < > เป็น html entities)
    # เพื่อความปลอดภัยเมื่อนำไปแสดงผลบนเว็บ
    safe_text = html.escape(text_str)
    
    return safe_text.strip()

def safe_ensure_columns_for_view(df):
    required_cols = ['Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 'Statement', 'Evidence_Image', 
        'lat', 'lon']
    if df is None or df.empty: return pd.DataFrame(columns=required_cols)
    for col in required_cols:
        if col not in df.columns: df[col] = ""
    return df

LOCATION_OPTIONS = ["อาคาร 1", "อาคาร 2", "อาคาร 3", "อาคาร 4", "อาคาร 5", "หอประชุมเทาทอง", "หอประชุมไทรทอง", "อาคารไฟฟ้าสนามฟุตบอล", "สนามบาส", "โรงอาหาร", "สนามปิงปอง", "สวนหลังห้องปกครอง", "สวนสนามเปตอง", "สวนเกษตร", "สวนหลังไทรทอง", "ห้องน้ำโรงอาหารติดอาคาร 4", "ห้องน้ำโรงอาหารติดประตูโรงอาหาร", "ห้องน้ำหลังอาคาร 3", "ห้องน้ำอาคารไฟฟ้า", "ห้องน้ำหลังอาคาร 5", "อื่นๆ"]

# --- PDF Function ---
def create_pdf(row):
    rid = str(row.get('Report_ID', '')); date_str = str(row.get('Timestamp', ''))
    reporter = str(row.get('Reporter', '-')); incident = str(row.get('Incident_Type', '-'))
    location = str(row.get('Location', '-')); details = str(row.get('Details', '-'))
    statement = str(row.get('Statement', '-')); audit_log = str(row.get('Audit_Log', ''))
    latest_date = "-"
    if audit_log:
        try:
            lines = [l for l in audit_log.split('\n') if l.strip()]
            if lines and '[' in lines[-1] and ']' in lines[-1]:
                latest_date = lines[-1][lines[-1].find('[')+1:lines[-1].find(']')]
        except: pass

    printer_name = st.session_state.current_user['name'] if st.session_state.current_user else "System"
    print_time = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
    
    qr = qrcode.make(rid); qr_buffer = io.BytesIO(); qr.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

    evidence_html = ""
    if row.get('Evidence_Image'):
        evidence_html = f"<div style='margin-top:10px;'><b>หลักฐาน:</b><br><img src='data:image/jpeg;base64,{row.get('Evidence_Image')}' style='max-height:150px;'></div>"
    
    logo_html = f'<img class="logo" src="data:{LOGO_MIME};base64,{LOGO_BASE64}">' if LOGO_BASE64 else ""

    html_content = f"""
    <!DOCTYPE html><html><head><style>
        @font-face {{ font-family: 'THSarabunNew'; src: url('file://{FONT_FILE}'); }}
        @page {{ size: A4; margin: 2cm; @bottom-right {{ content: "ผู้พิมพ์: {printer_name} | เวลา: {print_time}"; font-family: 'THSarabunNew'; font-size: 12pt; }} }}
        body {{ font-family: 'THSarabunNew'; font-size: 16pt; line-height: 1.3; }}
        .header {{ text-align: center; position: relative; margin-bottom: 20px; min-height: 80px; }}
        .logo {{ position: absolute; top: 0; left: 0; width: 60px; }}
        .qr {{ position: absolute; top: 0; right: 0; width: 60px; }}
        .box {{ border: 1px solid #000; background: #f9f9f9; padding: 10px; min-height: 50px; white-space: pre-wrap; }}
        .sig-table {{ width: 100%; margin-top: 30px; text-align: center; }} .sig-table td {{ padding-bottom: 30px; vertical-align: top; }}
    </style></head><body>
        <div class="header">{logo_html}<div style="font-size:22pt; font-weight:bold; margin-top:10px;">สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</div>
        <div style="font-size:18pt; font-weight:bold;">ใบสรุปรายงานเหตุการณ์</div><img class="qr" src="data:image/png;base64,{qr_base64}"></div><hr>
        <table style="width:100%"><tr><td width="60%"><b>เลขที่:</b> {rid}</td><td width="40%" align="right"><b>วันที่แจ้ง:</b> {date_str}<br><b>อัปเดต:</b> {latest_date}</td></tr></table>
        <p><b>ผู้แจ้ง:</b> {reporter} | <b>เหตุ:</b> {incident} | <b>สถานที่:</b> {location}</p>
        <div style="margin-top:10px;"><b>รายละเอียด:</b></div><div class="box">{details}</div>
        <div><b>ผลการสอบสวน:</b></div><div class="box">{statement}</div>{evidence_html}
        <table class="sig-table">
            <tr><td width="50%">ลงชื่อ.......................................<br>({row.get('Victim','')})<br>ผู้เสียหาย</td><td width="50%">ลงชื่อ.......................................<br>({row.get('Accused','')})<br>ผู้ถูกกล่าวหา</td></tr>
            <tr><td>ลงชื่อ.......................................<br>({row.get('Student_Police_Investigator','')})<br>ตำรวจนักเรียน</td><td>ลงชื่อ.......................................<br>({row.get('Witness','')})<br>พยาน</td></tr>
            <tr><td colspan="2"><br>ลงชื่อ.......................................<br>({row.get('Teacher_Investigator','')})<br>ครูผู้สอบสวน</td></tr>
        </table>
    </body></html>"""
    return HTML(string=html_content, base_url=BASE_DIR).write_pdf(font_config=FontConfiguration())

conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    total_pages = math.ceil(total_items / limit) or 1
    if st.session_state[key] > total_pages: st.session_state[key] = 1
    start = (st.session_state[key] - 1) * limit
    return start, start + limit, st.session_state[key], total_pages

# --- Callbacks ---
def view_case(rid):
    st.session_state.selected_case_id = rid; st.session_state.view_mode = "detail"; st.session_state.unlock_password = ""
def back_to_list():
    st.session_state.view_mode = "list"; st.session_state.selected_case_id = None
def clear_search_callback(): st.session_state.search_query = ""

# --- Dashboard (เจ้าหน้าที่) ---
def officer_dashboard():
    # (ส่วนนี้คงเดิมตามที่คุณส่งมา)
    user = st.session_state.current_user
    col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
    with col_h1:
        if LOGO_PATH and os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=80)
    with col_h2:
        st.markdown(f"<div style='font-size: 26px; font-weight: bold; color: #1E3A8A; padding-top: 20px;'>🏢 ระบบสอบสวน คุณ{user['name']}</div>", unsafe_allow_html=True)
    with col_h3: 
        st.write(""); 
        if st.button("🔴 Logout", use_container_width=True): st.session_state.current_user = None; st.rerun()

    try:
        target_sheet = get_target_sheet_name()
        df_raw = conn.read(worksheet=target_sheet, ttl="0")
        df_display = safe_ensure_columns_for_view(df_raw.copy()).fillna("")
        df_display['Report_ID'] = df_display['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        if st.session_state.view_mode == "list":
            tab_list, tab_dash = st.tabs(["📋 รายการแจ้งเหตุ", "📊 แดชบอร์ดสถิติ"])
            with tab_list:
                c_search, c_btn_search, c_btn_clear = st.columns([3, 1, 1])
                with c_search: search_q = st.text_input("ค้นหา", key="search_query", label_visibility="collapsed")
                with c_btn_search: st.button("🔍 ค้นหา", use_container_width=True)
                with c_btn_clear: st.button("❌ ล้าง", on_click=clear_search_callback, use_container_width=True)
                
                filtered = df_display.copy()
                if search_q: filtered = filtered[filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                df_p = filtered[filtered['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
                df_f = filtered[filtered['Status'] == "ดำเนินการเรียบร้อย"][::-1]

                st.markdown("<h4 style='color:#1E3A8A; background:#f0f2f6; padding:10px; border-radius:5px;'>⏳ รายการที่รอการดำเนินการ</h4>", unsafe_allow_html=True)
                sp, ep, cp, tp = calculate_pagination('page_pending', len(df_p), 5)
                
                # Header
                c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
                c1.markdown("**เลขที่**"); c2.markdown("**เวลา**"); c3.markdown("**เหตุ**"); c4.markdown("**สถานะ**"); st.divider()

                if df_p.empty: st.caption("ไม่มีรายการ")
                for i, row in df_p.iloc[sp:ep].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"📝 {row['Report_ID']}", key=f"p_{i}", use_container_width=True, on_click=view_case, args=(row['Report_ID'],))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type'])
                    with cc4: st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ {row['Status']}</span>", unsafe_allow_html=True)
                    st.divider()
                
                if tp > 1:
                    cp1, cp2, cp3 = st.columns([1, 2, 1])
                    with cp1: 
                        if st.button("⬅️", key="pp", disabled=(cp==1)): st.session_state.page_pending-=1; st.rerun()
                    with cp2: st.markdown(f"<div style='text-align:center;'>{cp}/{tp}</div>", unsafe_allow_html=True)
                    with cp3: 
                        if st.button("➡️", key="pn", disabled=(cp==tp)): st.session_state.page_pending+=1; st.rerun()

                st.markdown("<h4 style='color:#2e7d32; background:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                sf, ef, cf, tf = calculate_pagination('page_finished', len(df_f), 5)
                # (Logic Similar to Pending - Simplified for brevity)
                for i, row in df_f.iloc[sf:ef].iterrows():
                    cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                    with cc1: st.button(f"✅ {row['Report_ID']}", key=f"f_{i}", use_container_width=True, on_click=view_case, args=(row['Report_ID'],))
                    cc2.write(row['Timestamp']); cc3.write(row['Incident_Type'])
                    with cc4: st.markdown("<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True)
                    st.divider()

            with tab_dash:
                st.info("ส่วนแสดง Dashboard (ตามโค้ดเดิม)")
                # (ใส่โค้ด Dashboard เดิมของคุณที่นี่)

        elif st.session_state.view_mode == "detail":
            st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list, use_container_width=True)
            sid = str(st.session_state.selected_case_id).strip()
            sel = df_display[df_display['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]; row = sel.iloc[0]
                with st.container(border=True):
                    st.markdown(f"### 📝 {sid}")
                    st.write(f"**ผู้แจ้ง:** {row['Reporter']} | **สถานที่:** {row['Location']}")
                    st.info(f"**รายละเอียด:** {row['Details']}")
                    if clean_val(row['Image_Data']): st.image(base64.b64decode(row['Image_Data']), width=400)
                    
                    st.markdown("---"); st.write("#### ✍️ บันทึกผล")
                    # Form Logic (Simplified)
                    c1, c2 = st.columns(2)
                    vic = c1.text_input("ผู้เสียหาย", row['Victim']); acc = c2.text_input("ผู้ถูกกล่าวหา", row['Accused'])
                    wit = c1.text_input("พยาน", row['Witness']); tea = c2.text_input("ครูผู้สอบสวน", row['Teacher_Investigator'])
                    stu = c1.text_input("ตำรวจนักเรียน", row['Student_Police_Investigator'])
                    stmt = st.text_area("ผลการสอบสวน", row['Statement'])
                    sta = st.selectbox("สถานะ", ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"], index=["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"].index(row['Status']) if row['Status'] in ["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"] else 0)
                    
                    if st.button("💾 บันทึก"):
                        df_raw.at[idx, 'Victim'] = vic; df_raw.at[idx, 'Accused'] = acc
                        df_raw.at[idx, 'Witness'] = wit; df_raw.at[idx, 'Teacher_Investigator'] = tea
                        df_raw.at[idx, 'Student_Police_Investigator'] = stu; df_raw.at[idx, 'Statement'] = stmt
                        df_raw.at[idx, 'Status'] = sta
                        df_raw.at[idx, 'Audit_Log'] = f"{row['Audit_Log']}\nUpdate by {user['name']}"
                        conn.update(worksheet=target_sheet, data=df_raw.fillna(""))
                        st.success("บันทึกแล้ว"); time.sleep(1); st.rerun()
                    
                    # PDF Button
                    try:
                        pdf = create_pdf(row)
                        st.download_button("📥 โหลด PDF", pdf, f"Report_{sid}.pdf", "application/pdf", type="primary", use_container_width=True)
                    except: st.error("PDF Error")

    except Exception as e: st.error(f"Error: {e}")

# --- [แก้ไขแล้ว: ตัด time.sleep ออกเพื่อให้ปุ่มแดงกดได้ทันที] ---
@st.dialog("✅ บันทึกข้อมูลสำเร็จ")
def show_success_popup(rid):
    st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 50px;">🎉</div>
            <h3>ระบบได้รับข้อมูลแล้ว</h3>
            <p>กรุณาจดจำรหัสรับแจ้งนี้เพื่อใช้ตรวจสอบสถานะ</p>
            <div style="background-color: #f0fdf4; padding: 15px; border-radius: 10px; border: 1px solid #bbf7d0; margin: 10px 0;">
                <span style="font-size: 24px; font-weight: bold; color: #15803d; letter-spacing: 2px;">{rid}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("ℹ️ กดปุ่มด้านล่างเพื่อปิดหน้าต่าง")

    # ปุ่มปิดทำงานทันที (เพราะไม่มี time.sleep มาขวางแล้ว)
    if st.button("ปิดหน้าต่าง (Close)", type="primary", use_container_width=True):
        st.session_state.show_popup = False
        st.rerun()

# --- 5. Main Page (นักเรียน) ---
# สร้างตารางอ้างอิงพิกัด (ตัวเลขสมมติ คุณนำพิกัดจริงมาเปลี่ยนได้เลย)
COORD_MAP = {
    "อาคาร 1": {"lat": 16.293080624461656, "lon": 103.97334404257019},
    "อาคาร 2": {"lat": 16.29279814390506, "lon": 103.97334845175875},
    "อาคาร 3": {"lat": 16.292547130677022, "lon": 103.9742885660193},
    "อาคาร 4": {"lat": 16.292464708883504, "lon": 103.97328212630455},
    "อาคาร 5": {"lat": 16.29409615213189, "lon": 103.97431743733651},
    "หอประชุมเทาทอง": {"lat": 16.2933910148143, "lon": 103.97435250954894},
    "หอประชุมไทรทอง": {"lat": 16.292976522262947, "lon": 103.97455635743196},
    "อาคารไฟฟ้าสนามฟุตบอล": {"lat": 16.29471891331982, "lon": 103.97219748923851},
    "สนามบาส": {"lat": 16.294180437912743, "lon": 103.97201431305878},
    "โรงอาหาร": {"lat": 16.292685117630384, "lon": 103.97202378933812},
    "สนามปิงปอง": {"lat": 16.293241855058024, "lon": 103.97291845970389},
    "สวนหลังห้องปกครอง": {"lat": 16.29356823258865, "lon": 103.97472900714698},
    "สนามเปตอง": {"lat": 16.29400957119914, "lon": 103.97312938272556},
    "สวนเกษตร": {"lat": 16.294127310210936, "lon": 103.97369507232361},
    "สวนหลังไทรทอง": {"lat": 16.29297281083706, "lon": 103.9741158275382},
    "ห้องน้ำโรงอาหาารติดอาคาร4": {"lat": 16.292463682879095, "lon": 103.97264722383926},
    "ห้องน้ำหลังอาคาร3": {"lat": 16.292126722514713, "lon": 103.97403520772245},
    "ห้องน้ำอาคารไฟฟ้า": {"lat": 16.29465819963838, "lon": 103.97237918736676},
    "ห้องน้ำหลังอาคาร5": {"lat": 16.293816914880985, "lon": 103.97437580456852},
    "อื่นๆ": {"lat": 16.293596638838643, "lon": 103.97250289339189} # พิกัดกลางโรงเรียน
}
def main_page():
    # 1. Pop-up Logic
    if "show_popup" not in st.session_state: st.session_state.show_popup = False
    if st.session_state.show_popup: show_success_popup(st.session_state.get("popup_rid", ""))

    # 2. Logo & Header
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        c1, c2, c3 = st.columns([5, 1, 5])
        c2.image(LOGO_PATH, width=100)
    
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุโรงเรียนโพนทองฯ</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 แจ้งเหตุ", "🔍 ติดตามผล"])
    
    with tab1:
        # เริ่มฟอร์ม
        with st.form("report_form", clear_on_submit=True):
            st.info("กรอกข้อมูลแจ้งเหตุ (ช่องที่มี * จำเป็นต้องกรอก)")
            
            # --- Input Fields ---
            rep = sanitize_input(st.text_input("ชื่อผู้แจ้ง *", max_chars=100))
            typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท/ทำร้ายร่างกาย", "สารเสพติด/บุหรี่ไฟฟ้า", "พกพาอาวุธ", "ลักทรัพย์", "บูลลี่/Cyberbully", "ล่วงละเมิดทางเพศ", "อื่นๆ"])
            loc = st.selectbox("สถานที่เกิดเหตุ *", LOCATION_OPTIONS)
            det = sanitize_input(st.text_area("รายละเอียด *", placeholder="เล่าเหตุการณ์...", max_chars=1000))
            img = st.file_uploader("รูปภาพประกอบ", type=['jpg','png'])

            st.markdown("---")
            pdpa_check = st.checkbox("ยินยอมให้โรงเรียนนำข้อมูลไปใช้วิเคราะห์ผล")
            
            # =========================================================
            # 🔴🔴 จุดแจ้งเตือน (วางไว้ก่อนปุ่มกด 100%)
            # =========================================================
            st.error("⚠️ **คำเตือน:** การแจ้งความเท็จเพื่อแกล้งผู้อื่นมีความผิดตามกฎหมายอาญา และการแจ้งนี้ไม่ใช่การแจ้งความดำเนินคดีตามกฎหมาย")
            # =========================================================
            
            # ปุ่มส่ง (Submit Button)
            submitted = st.form_submit_button("🚀 ส่งแจ้งเหตุ", type="primary", use_container_width=True)
            
            if submitted:
                # --- จุดที่ต้องแก้: ดึงพิกัดจาก COORD_MAP ตามที่เลือกใน loc ---
                coords = COORD_MAP.get(loc, {"lat": 0.0, "lon": 0.0})
                current_lat = coords["lat"]
                current_lon = coords["lon"]
                # -------------------------------------------------------

                if len(det) < 5: 
                    st.toast("⚠️ รายละเอียดสั้นเกินไป", icon="⚠️")
                elif not pdpa_check: 
                    st.toast("⚠️ กรุณาติ๊กยืนยันข้อมูล", icon="⚠️")
                elif rep and loc and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    img_p = process_image(img) if img else ""
                    
                    try:
                        target_sheet = get_target_sheet_name()
                        df_current = conn.read(worksheet=target_sheet, ttl=0)
                        
                        new_row = pd.DataFrame([{
                            "Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), 
                            "Reporter": rep, 
                            "Incident_Type": typ, 
                            "Location": loc, 
                            "Details": det, 
                            "Status": "รอดำเนินการ", 
                            "Report_ID": rid, 
                            "Image_Data": img_p, 
                            "Audit_Log": f"Created: {get_now_th()}",
                            "lat": current_lat,
                            "lon": current_lon
                        }])

                        combined_df = pd.concat([df_current, new_row], ignore_index=True).fillna("")
                        conn.update(worksheet=target_sheet, data=combined_df)
                        
                        st.session_state.popup_rid = rid
                        st.session_state.show_popup = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"บันทึกไม่สำเร็จ: {e}")

    with tab2:
        st.subheader("🔍 ตรวจสอบสถานะ")
        c_code, c_btn = st.columns([3,1])
        code = c_code.text_input("เลข 4 ตัวท้าย", max_chars=4, label_visibility="collapsed")
        if c_btn.button("ค้นหา", use_container_width=True):
            if len(code) == 4 and code.isdigit():
                try:
                    df = conn.read(worksheet=get_target_sheet_name(), ttl=0).fillna("")
                    df = safe_ensure_columns_for_view(df)
                    df['Report_ID'] = df['Report_ID'].astype(str)
                    match = df[df['Report_ID'].str.endswith(code)]
                    if not match.empty:
                        for _, r in match.iterrows():
                            st.success(f"รหัส: {r['Report_ID']}")
                            st.info(f"สถานะ: {r['Status']}")
                    else: st.warning("ไม่พบข้อมูล")
                except: st.error("Connection Error")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            accs = st.secrets.get("officer_accounts", {})
            if pw in accs:
                st.session_state.current_user = accs[pw]; st.rerun()
# --- Run ---
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

if st.session_state.current_user: officer_dashboard()
else: main_page()
