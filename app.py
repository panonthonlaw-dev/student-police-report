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
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from PIL import Image

# --- 1. ตั้งค่าหน้าจอและซ่อนเมนู ---
st.set_page_config(page_title="ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา", page_icon="👮‍♂️", layout="wide")

st.markdown("""
<style>
    /* ซ่อน Menu Bar และ Header */
    [data-testid="stHeader"] { display: none; }
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; }
    footer { visibility: hidden; height: 0%; }
    .stDeployButton { display: none; }
    [data-testid="stSidebar"] { display: none; }
    
    /* ปรับ Layout ให้ชิดขอบ */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    
    /* ปรับแต่ง Card */
    .metric-card { 
        background: white; padding: 10px; border-radius: 8px; 
        border: 1px solid #d1d5db; text-align: center; box-shadow: none !important; 
    }
    .metric-value { font-size: 2.2rem; font-weight: 800; color: #1e293b; }
    .metric-label { font-size: 0.9rem; color: #64748b; }
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
    # ตัดรอบเดือนพฤษภาคม
    if now.month < 5: ac_year = year_th - 1
    else: ac_year = year_th
    return f"Investigation_{ac_year}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# ค้นหาไฟล์โลโก้
LOGO_PATH = None
possible_logos = glob.glob(os.path.join(BASE_DIR, "school_logo*"))
if possible_logos:
    LOGO_PATH = possible_logos[0]

def get_base64_image(image_path):
    if not image_path or not os.path.exists(image_path): return ""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

LOGO_BASE64 = get_base64_image(LOGO_PATH) if LOGO_PATH else ""
LOGO_MIME = "image/png"

def sanitize_input(text):
    if text: return str(text).replace("=", "").replace('"', "").replace("'", "").strip()
    return text

# ฟังก์ชันจัดการรูปภาพ (ลดขนาดไฟล์เพื่อป้องกัน Error 50,000 chars)
def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        if img.mode in ('RGBA', 'LA', 'P'): img = img.convert('RGB')
        
        # ลดขนาดภาพลงให้เหลือพอดีๆ
        img.thumbnail((450, 450)) 
        
        buffer = io.BytesIO()
        # ลดคุณภาพ JPEG ลงเพื่อประหยัดพื้นที่
        img.save(buffer, format="JPEG", quality=40, optimize=True)
        
        base64_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Safety Guard: ถ้ายังยาวเกิน 50,000 ตัวอักษร ให้ตัดทิ้ง
        if len(base64_str) > 49500:
            st.warning("⚠️ รูปภาพมีรายละเอียดสูงเกินไป ระบบจำเป็นต้องตัดรูปออกเพื่อบันทึกข้อมูลส่วนอื่น")
            return ""
            
        return base64_str
    except: return ""

def safe_ensure_columns_for_view(df):
    required_cols = [
        'Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 
        'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 
        'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 
        'Statement', 'Evidence_Image'
    ]
    if df is None or df.empty: return pd.DataFrame(columns=required_cols)
    for col in required_cols:
        if col not in df.columns: df[col] = ""
    return df

LOCATION_OPTIONS = [
    "อาคาร 1", "อาคาร 2", "อาคาร 3", "อาคาร 4", "อาคาร 5",
    "หอประชุมเทาทอง", "หอประชุมไทรทอง", "อาคารไฟฟ้าสนามฟุตบอล", "สนามบาส", 
    "โรงอาหาร", "สนามปิงปอง", "สวนหลังห้องปกครอง", "สวนสนามเปตอง", 
    "สวนเกษตร", "สวนหลังไทรทอง", "ห้องน้ำโรงอาหารติดอาคาร 4", 
    "ห้องน้ำโรงอาหารติดประตูโรงอาหาร", "ห้องน้ำหลังอาคาร 3", 
    "ห้องน้ำอาคารไฟฟ้า", "ห้องน้ำหลังอาคาร 5", "อื่นๆ"
]

# ฟังก์ชันสร้าง PDF (ตัดทอนเพื่อความกระชับ)
def create_pdf(row):
    # (ใช้โค้ดสร้าง PDF เดิมของคุณได้เลยครับ ผมละไว้เพื่อความกระชับ)
    return b"" 

conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    total_pages = math.ceil(total_items / limit) or 1
    if st.session_state[key] > total_pages: st.session_state[key] = 1
    start = (st.session_state[key] - 1) * limit
    return start, start + limit, st.session_state[key], total_pages

# --- Callbacks ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

# --- Pop-up Dialog ---
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
    
    st.warning("⚠️ หน้าต่างนี้จะปิดอัตโนมัติใน 1 นาที")
    
    if st.button("ปิดหน้าต่าง (Close)", type="primary", use_container_width=True):
        st.session_state.show_popup = False
        st.rerun()
        
    time.sleep(60)
    st.session_state.show_popup = False
    st.rerun()

# --- Main Page Function ---
def main_page():
    # 1. แสดง Pop-up ถ้ามี flag
    if "show_popup" not in st.session_state: st.session_state.show_popup = False
    if st.session_state.show_popup:
        show_success_popup(st.session_state.get("popup_rid", ""))

    # 2. แสดง Logo
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        c1, c2, c3 = st.columns([5, 1, 5])
        c2.image(LOGO_PATH, width=100)
    
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ ระบบแจ้งเหตุสถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 แจ้งเหตุใหม่", "🔍 ติดตามสถานะ"])
    
    with tab1:
        with st.form("report_form", clear_on_submit=True):
            rep = sanitize_input(st.text_input("ชื่อผู้แจ้ง *"))
            typ = st.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท/ทำร้ายร่างกาย", "สารเสพติด/บุหรี่ไฟฟ้า/เครื่องดื่มผิดกฎหมาย", "พกพาอาวุธ", "ลักทรัพย์/ทำลายทรัพย์สิน", "บูลลี่/ข่มขู่/ด่าทอบนโลกออนไลน์", "ล่วงละเมิด/คุกคามทางเพศ", "อื่นๆ"])
            loc = st.selectbox("สถานที่เกิดเหตุ *", LOCATION_OPTIONS)
            det = sanitize_input(st.text_area("รายละเอียดเหตุการณ์ *", placeholder="ระบุรายละเอียดให้ชัดเจน (อย่างน้อย 10 ตัวอักษร)"))
            img = st.file_uploader("แนบรูปภาพประกอบ (ถ้ามี)", type=['jpg','png'])
            
            st.markdown("---")
            pdpa_check = st.checkbox("ข้าพเจ้ายินยอมให้เก็บรวบรวมข้อมูลเพื่อใช้ในการดำเนินงาน...")
            
            submitted = st.form_submit_button("ส่งข้อมูลแจ้งเหตุ", use_container_width=True)
            
            if submitted:
                # Validation Checks
                if 'last_submit_time' in st.session_state:
                    time_diff = (datetime.now() - st.session_state.last_submit_time).total_seconds()
                    if time_diff < 60:
                        st.error(f"⚠️ กรุณารออีก {60 - int(time_diff)} วินาที")
                        st.stop()

                if len(det) < 10: st.error("⚠️ กรุณาระบุรายละเอียดให้ชัดเจนกว่านี้")
                elif not pdpa_check: st.warning("⚠️ กรุณากดยินยอม PDPA")
                elif rep and loc and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    
                    # --- [เริ่มระบบบันทึกแบบปลอดภัยสูงสุด] ---
                    try:
                        target_sheet = get_target_sheet_name()
                        df_old = None
                        
                        # 1. Retry Reading
                        for _ in range(3):
                            try:
                                temp_df = conn.read(worksheet=target_sheet, ttl=0)
                                if temp_df is not None: df_old = temp_df; break
                            except: time.sleep(1)
                        
                        # 2. Safety Guards (ป้องกันข้อมูลหาย)
                        if df_old is None:
                            st.error("🚨 วิกฤต: เชื่อมต่อฐานข้อมูลไม่ได้ (Connection Failed)"); st.stop()
                        
                        if 'Report_ID' not in df_old.columns:
                            # ยอมให้ผ่านถ้าเป็นชีตใหม่ (0 rows)
                            if not df_old.empty:
                                st.error("🚨 วิกฤต: โครงสร้างข้อมูลผิดพลาด (No Report_ID)"); st.stop()

                        # 3. Prepare New Data
                        img_processed = process_image(img) if img else ""
                        new_data = pd.DataFrame([{
                            "Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), 
                            "Reporter": rep, "Incident_Type": typ, "Location": loc, 
                            "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, 
                            "Image_Data": img_processed,
                            "Audit_Log": f"สร้างเมื่อ: {get_now_th().strftime('%d/%m/%Y %H:%M')}"
                        }])
                        
                        # 4. Merge Safely
                        for c in df_old.columns:
                            if c not in new_data.columns: new_data[c] = ""
                        
                        combined_df = pd.concat([df_old, new_data], ignore_index=True).fillna("")
                        
                        # Guard: ข้อมูลต้องไม่ลดลง
                        if len(combined_df) <= len(df_old):
                            st.error("🚨 วิกฤต: ข้อมูลสูญหายระหว่างประมวลผล"); st.stop()

                        # 5. Save & Cache Clear
                        conn.update(worksheet=target_sheet, data=combined_df)
                        st.cache_data.clear()
                        st.session_state.last_submit_time = datetime.now()
                        
                        # 6. Trigger Pop-up
                        st.session_state.popup_rid = rid
                        st.session_state.show_popup = True
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                        st.warning("⚠️ ข้อมูลยังไม่ถูกบันทึก กรุณาลองใหม่")
                    # --- [สิ้นสุดระบบบันทึก] ---
                else: st.error("กรุณากรอกข้อมูลให้ครบถ้วน")

    with tab2:
        st.subheader("🔍 ตรวจสอบสถานะ")
        search_code = st.text_input("เลข 4 ตัวท้ายของรหัสรับแจ้ง", max_chars=4)
        if st.button("🔎 ค้นหา", use_container_width=True):
            if len(search_code) == 4 and search_code.isdigit():
                try:
                    target_sheet = get_target_sheet_name()
                    df = conn.read(worksheet=target_sheet, ttl="0")
                    df = safe_ensure_columns_for_view(df).fillna("")
                    df['Report_ID'] = df['Report_ID'].astype(str)
                    match = df[df['Report_ID'].str.endswith(search_code)]
                    
                    if not match.empty:
                        for _, row in match.iterrows():
                            with st.container(border=True):
                                st.markdown(f"#### 📌 {row['Report_ID']}")
                                st.info(f"สถานะ: {row['Status']}")
                                st.caption(f"เมื่อ: {row['Timestamp']}")
                    else: st.warning("ไม่พบข้อมูล")
                except Exception as e: st.error(f"Error: {e}")
            else: st.error("กรุณากรอกเลข 4 หลัก")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            accounts = st.secrets.get("officer_accounts", {})
            if pw in accounts:
                st.session_state.current_user = accounts[pw]
                st.rerun()
            else: st.error("รหัสผิด")

def officer_dashboard():
    st.title("Officer Dashboard")
    if st.button("Logout"):
        st.session_state.current_user = None
        st.rerun()

# --- Run Application ---
if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
