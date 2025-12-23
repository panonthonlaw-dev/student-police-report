import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz, random, os, base64, io, qrcode, glob, math, mimetypes, json, requests, re, textwrap, time
from PIL import Image

# PDF Libraries
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except: pass
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import plotly.express as px

# ==========================================
# 1. INITIAL SETTINGS & SESSION STATE
# ==========================================
st.set_page_config(page_title="ศูนย์แจ้งเหตุโรงเรียนโพนทองพัฒนาวิทยา", page_icon="🚨", layout="wide")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = {}
if "current_dept" not in st.session_state: st.session_state.current_dept = None
if "current_user" not in st.session_state: st.session_state.current_user = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'selected_case_id' not in st.session_state: st.session_state.selected_case_id = None
if 'unlock_password' not in st.session_state: st.session_state.unlock_password = ""
if 'page_pending' not in st.session_state: st.session_state.page_pending = 1
if 'page_finished' not in st.session_state: st.session_state.page_finished = 1

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# --- โลโก้ ---
LOGO_PATH = next((f for f in glob.glob(os.path.join(BASE_DIR, "school_logo*")) if os.path.isfile(f)), None)
def get_base64_image(image_path):
    if not image_path or not os.path.exists(image_path): return ""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')
LOGO_BASE64 = get_base64_image(LOGO_PATH) if LOGO_PATH else ""

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_now_th(): return datetime.now(pytz.timezone('Asia/Bangkok'))

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", ""] or val is None: return ""
    return str(val).strip()

def safe_ensure_columns_for_view(df):
    required_cols = ['Report_ID', 'Timestamp', 'Reporter', 'Incident_Type', 'Location', 'Details', 'Status', 'Image_Data', 'Audit_Log', 'Victim', 'Accused', 'Witness', 'Teacher_Investigator', 'Student_Police_Investigator', 'Statement', 'Evidence_Image']
    df_new = df.copy()
    for col in required_cols:
        if col not in df_new.columns: df_new[col] = ""
    return df_new

def calculate_pagination(key, total_items, limit=5):
    if key not in st.session_state: st.session_state[key] = 1
    total_pages = math.ceil(total_items / limit) or 1
    if st.session_state[key] > total_pages: st.session_state[key] = 1
    start_idx = (st.session_state[key] - 1) * limit
    return start_idx, start_idx + limit, st.session_state[key], total_pages

def process_image(img_file):
    if img_file is None: return ""
    try:
        img = Image.open(img_file)
        if img.mode in ('RGBA', 'LA', 'P'): img = img.convert('RGB')
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=65, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

# --- PDF Function (Investigation) ---
def create_inv_pdf(row):
    # (ใช้ Logic เดิมของคุณตรงนี้ได้เลย ผมย่อเพื่อความกระชับ)
    rid = str(row.get('Report_ID', ''))
    # ... [ใส่ Code PDF เดิมของคุณตรงนี้] ...
    # (เพื่อไม่ให้ยาวเกินไป ผมขอละไว้ในฐานที่เข้าใจว่าใช้ฟังก์ชันเดิมของคุณครับ)
    pass 

# ==========================================
# 3. STUDENT REPORTING PAGE (หน้าแจ้งเหตุ)
# ==========================================
def student_report_page():
    # Header
    if LOGO_PATH:
        c1, c2, c3 = st.columns([5, 1, 5])
        c2.image(LOGO_PATH, width=100)
    
    st.markdown("<h1 style='text-align: center; color: #b91c1c;'>🚨 แจ้งเหตุด่วน / พฤติกรรมไม่เหมาะสม</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #4b5563;'>โรงเรียนโพนทองพัฒนาวิทยา</h4>", unsafe_allow_html=True)
    st.info("ℹ️ ข้อมูลของท่านจะถูกเก็บเป็นความลับ และส่งตรงถึงเจ้าหน้าที่ฝ่ายกิจการนักเรียน")

    with st.form("student_report_form"):
        col1, col2 = st.columns(2)
        reporter_name = col1.text_input("ชื่อผู้แจ้ง (ไม่ระบุก็ได้)", placeholder="เช่น พลเมืองดี")
        incident_type = col2.selectbox("ประเภทเหตุ", ["ทะเลาะวิวาท", "สูบบุหรี่/สารเสพติด", "ชู้สาว", "หนีเรียน", "อุบัติเหตุ", "กลั่นแกล้ง (Bully)", "อื่นๆ"])
        
        location = st.text_input("สถานที่เกิดเหตุ *", placeholder="เช่น ห้องน้ำชาย อาคาร 4, โรงอาหาร")
        details = st.text_area("รายละเอียดเหตุการณ์ *", placeholder="อธิบายสิ่งที่พบเห็น ใครทำอะไร ที่ไหน อย่างไร...", height=150)
        
        uploaded_img = st.file_uploader("📸 แนบรูปภาพประกอบ (ถ้ามี)", type=['jpg', 'png', 'jpeg'])
        
        submitted = st.form_submit_button("📤 ส่งแจ้งเหตุ", type="primary", use_container_width=True)
        
        if submitted:
            if not location or not details:
                st.error("⚠️ กรุณาระบุสถานที่และรายละเอียดเหตุการณ์")
            else:
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_old = conn.read(ttl="0")
                    
                    # สร้างข้อมูลใหม่
                    rid = f"R-{random.randint(10000, 99999)}"
                    timestamp = get_now_th().strftime('%d/%m/%Y %H:%M')
                    img_data = process_image(uploaded_img) if uploaded_img else ""
                    
                    new_row = pd.DataFrame([{
                        'Report_ID': rid,
                        'Timestamp': timestamp,
                        'Reporter': reporter_name if reporter_name else "ไม่ประสงค์ออกนาม",
                        'Incident_Type': incident_type,
                        'Location': location,
                        'Details': details,
                        'Status': "รอดำเนินการ",
                        'Image_Data': img_data,
                        'Audit_Log': f"[{timestamp}] รับแจ้งเข้าระบบ",
                        'Victim': '', 'Accused': '', 'Witness': '', 
                        'Teacher_Investigator': '', 'Student_Police_Investigator': '', 
                        'Statement': '', 'Evidence_Image': ''
                    }])
                    
                    # รวมและบันทึก
                    df_combined = pd.concat([df_old, new_row], ignore_index=True)
                    conn.update(data=df_combined)
                    
                    st.success(f"✅ ส่งข้อมูลสำเร็จ! รหัสอ้างอิงของคุณคือ: {rid}")
                    st.balloons()
                    time.sleep(3)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    # ปุ่ม Login เจ้าหน้าที่ (ซ่อนด้านล่าง)
    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่ (Officer Login)"):
        pwd = st.text_input("รหัสผ่านระบบ", type="password")
        if st.button("เข้าสู่ระบบ"):
            accs = st.secrets.get("OFFICER_ACCOUNTS", {})
            if pwd in accs:
                st.session_state.logged_in = True
                st.session_state.user_info = accs[pwd]
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# ==========================================
# 4. OFFICER PORTAL (ระบบเจ้าหน้าที่)
# ==========================================
def investigation_module():
    # ... [โค้ด investigation_module เดิมของคุณ ใส่ตรงนี้] ...
    # (เพื่อความกระชับ ผมขอเว้นไว้ ให้คุณ copy code ส่วนนี้จากอันเดิมมาใส่ได้เลยครับ)
    pass

def traffic_module():
    # ... [โค้ด traffic_module เดิมของคุณ ใส่ตรงนี้] ...
    pass

def officer_dashboard():
    # Header เจ้าหน้าที่
    user = st.session_state.user_info
    st.sidebar.title(f"👤 {user.get('name', 'Officer')}")
    st.sidebar.info(f"สถานะ: {user.get('role', 'staff')}")
    
    if st.sidebar.button("🚪 ออกจากระบบ"):
        st.session_state.logged_in = False
        st.session_state.current_dept = None
        st.rerun()

    # เลือกแผนก
    if st.session_state.current_dept is None:
        st.title("🏢 ศูนย์ปฏิบัติการเจ้าหน้าที่")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🕵️ ระบบงานสอบสวน (รับแจ้งเหตุ)", use_container_width=True, type="primary"):
                st.session_state.current_dept = "inv"
                st.rerun()
        with c2:
            if st.button("🚦 ระบบงานจราจร (ตรวจสอบรถ)", use_container_width=True, type="primary"):
                st.session_state.current_dept = "tra"
                st.rerun()
    else:
        # ปุ่มย้อนกลับ
        if st.sidebar.button("🔄 เปลี่ยนแผนกงาน"):
            st.session_state.current_dept = None
            st.rerun()
            
        if st.session_state.current_dept == "inv":
            # เรียกฟังก์ชันงานสอบสวนเดิมของคุณ
            investigation_module()
        elif st.session_state.current_dept == "tra":
            # เรียกฟังก์ชันงานจราจรเดิมของคุณ
            st.title("🚦 ระบบจราจร")
            # traffic_module() # เปิดใช้งานเมื่อใส่โค้ดแล้ว

# ==========================================
# 5. MAIN ROUTING
# ==========================================
def main():
    if not st.session_state.logged_in:
        student_report_page() # หน้าแรกคือนักเรียนแจ้งเหตุ
    else:
        officer_dashboard()   # หน้าเจ้าหน้าที่

if __name__ == "__main__":
    main()
