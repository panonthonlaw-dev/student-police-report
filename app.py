import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import random
import os
import base64
import time
from fpdf import FPDF
from PIL import Image
import io

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

LOGO_FILE = "school_logo.png"
FONT_FILE = "THSarabunNew.ttf"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

# --- 2. ระบบจัดการ State ---
def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"

def back_to_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

if 'current_user' not in st.session_state: st.session_state.current_user = None
if 'submitted_id' not in st.session_state: st.session_state.submitted_id = None
if 'last_activity' not in st.session_state: st.session_state.last_activity = get_now_th()
if 'view_mode' not in st.session_state: st.session_state.view_mode = "list"
if 'selected_case_id' not in st.session_state: st.session_state.selected_case_id = None

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .report-id-box { background-color: #f0f9ff; border: 2px solid #1E3A8A; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }
    div[data-testid="column"] button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() in ["nan", "none", "nat", ""] or val is None: return ""
    return str(val).strip()

# --- 3. ข้อมูลบัญชี ---
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
    if elapsed > 1800:
        st.session_state.current_user = None
        st.session_state.view_mode = "list"
        st.rerun()
    else:
        st.session_state.last_activity = get_now_th()

# --- 4. ฟังก์ชัน PDF ---
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
        pdf.cell(90, 8, txt=f"เลขที่รับแจ้ง: {clean_val(row_data.get('Report_ID'))}")
        pdf.cell(90, 8, txt=f"วันที่แจ้งเหตุ: {clean_val(row_data.get('Timestamp'))}", align='R', ln=True)
        pdf.ln(5)
        pdf.multi_cell(0, 8, txt=f"ประเภทเหตุ: {clean_val(row_data.get('Incident_Type'))} | สถานที่: {clean_val(row_data.get('Location'))}")
        pdf.multi_cell(0, 8, txt=f"รายละเอียดเหตุการณ์เดิม: {clean_val(row_data.get('Details'))}")
        
        pdf.ln(5); pdf.set_font('ThaiFont', '', 15); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14); pdf.multi_cell(0, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        pdf.ln(10); pdf.set_font('ThaiFont', '', 14)
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", align='C')
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Victim'))} )", align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Accused'))} )", ln=True, align='C')
        pdf.cell(90, 8, txt="ผู้เสียหาย", align='C')
        pdf.cell(90, 8, txt="ผู้ถูกกล่าวหา", ln=True, align='C')
        pdf.ln(5)
        
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", align='C')
        pdf.cell(90, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Student_Police_Investigator'))} )", align='C')
        pdf.cell(90, 8, txt=f"( {clean_val(row_data.get('Witness'))} )", ln=True, align='C')
        pdf.cell(90, 8, txt="ตำรวจนักเรียนผู้สอบสวน", align='C')
        pdf.cell(90, 8, txt="พยาน", ln=True, align='C')
        pdf.ln(5)
        
        pdf.cell(0, 8, txt="ลงชื่อ..........................................................", ln=True, align='C')
        pdf.cell(0, 8, txt=f"( {clean_val(row_data.get('Teacher_Investigator'))} )", ln=True, align='C')
        pdf.cell(0, 8, txt="ครูผู้สอบสวน / หัวหน้างานปกครอง", ln=True, align='C')

        pdf.set_y(-20); pdf.set_font('ThaiFont', '', 10)
        printer = st.session_state.current_user['name'] if st.session_state.current_user else "System"
        pdf.cell(0, 5, txt=f"พิมพ์โดย: {printer} | {get_now_th().strftime('%d/%m/%Y %H:%M:%S')}", align='R')
        return pdf.output()
    except Exception as e: return str(e)

# --- 5. Dashboard ---
def officer_dashboard():
    user = st.session_state.current_user
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"<div class='main-header'>🏢 ระบบจัดการ (คุณ{user['name']})</div>", unsafe_allow_html=True)
    with col_h2: 
        if st.button("🔴 Logout", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.view_mode = "list"
            st.rerun()

    try:
        df = conn.read(ttl=0)
        df.columns = df.columns.str.strip()
        if 'Report_ID' not in df.columns: df['Report_ID'] = ""
        df = df.fillna("")
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True)

        # --- LIST MODE ---
        if st.session_state.view_mode == "list":
            st.info("💡 **คลิกที่ปุ่มเลขที่รับแจ้ง** เพื่อเข้าไปดูรายละเอียด, แก้ไข, หรือพิมพ์ PDF")
            
            c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
            c1.markdown("**เลขที่รับแจ้ง (คลิก)**")
            c2.markdown("**วันเวลา**")
            c3.markdown("**ประเภทเหตุ**")
            c4.markdown("**สถานะ**")
            st.markdown("---")

            for index, row in df.iloc[::-1].iterrows():
                raw_rid = str(row.get('Report_ID', '')).strip()
                rid_label = raw_rid if raw_rid and raw_rid.lower() not in ["nan", "none", ""] else "⚠️ ไม่พบเลข (กดดู)"
                real_rid = raw_rid

                has_result = clean_val(row.get('Statement')) != ""
                
                cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                
                with cc1:
                    # ปุ่มเดียวกดเข้าไปดูได้หมด
                    btn_label = f"✅ {rid_label}" if has_result else f"📝 {rid_label}"
                    st.button(
                        btn_label, 
                        key=f"btn_{index}", 
                        use_container_width=True,
                        on_click=view_case, 
                        args=(real_rid,)
                    )
                
                with cc2: st.write(row.get('Timestamp', '-'))
                with cc3: st.write(row.get('Incident_Type', '-'))
                with cc4:
                    if has_result:
                        st.markdown(f"<span style='color:green;font-weight:bold'>✅ เรียบร้อย</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ รอสอบสวน</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

        # --- DETAIL MODE ---
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
                    
                    st.write("#### ✍️ บันทึก/แก้ไข ผลการสอบสวน")
                    f1, f2 = st.columns(2)
                    with f1:
                        v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=not is_admin)
                        v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=not is_admin)
                        v_wit = st.text_input("พยาน *", value=clean_val(row.get('Witness')), disabled=not is_admin)
                    with f2:
                        v_tea = st.text_input("ครูผู้สอบสวน *", value=clean_val(row.get('Teacher_Investigator')), disabled=not is_admin)
                        v_stu = st.text_input("ตำรวจนักเรียนสอบสวน *", value=clean_val(row.get('Student_Police_Investigator')), disabled=not is_admin)
                        opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                        curr = row.get('Status', 'รอดำเนินการ')
                        idx_stat = opts.index(curr) if curr in opts else 0
                        v_sta = st.selectbox("สถานะ", opts, index=idx_stat, disabled=not is_admin)
                    
                    v_stmt = st.text_area("บันทึกคำให้การ/ผลการดำเนินการ *", value=clean_val(row.get('Statement')), disabled=not is_admin)

                    # ปุ่มบันทึก (Admin)
                    if is_admin:
                        is_complete = all([v_vic, v_acc, v_wit, v_tea, v_stu, v_stmt])
                        if st.button("💾 บันทึกข้อมูล", type="secondary", use_container_width=True, disabled=not is_complete):
                            df.at[idx, 'Victim'] = v_vic; df.at[idx, 'Accused'] = v_acc
                            df.at[idx, 'Witness'] = v_wit; df.at[idx, 'Teacher_Investigator'] = v_tea
                            df.at[idx, 'Student_Police_Investigator'] = v_stu; df.at[idx, 'Status'] = v_sta
                            df.at[idx, 'Statement'] = v_stmt; df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            st.toast("✅ บันทึกเรียบร้อย!"); st.success("บันทึกสำเร็จ!")
                            time.sleep(1.5); st.rerun()
                        if not is_complete: st.caption("⚠️ กรอกข้อมูล (*) ให้ครบเพื่อบันทึก")

                    # --- ส่วนแสดงปุ่มพิมพ์ PDF (แสดงตลอดเวลา อยู่ล่างสุด) ---
                    st.markdown("---")
                    st.write("#### 📄 เอกสาร")
                    
                    has_stmt = clean_val(row.get('Statement')) != ""
                    
                    # สร้าง PDF
                    pdf_bytes = create_pdf(row)
                    
                    if has_stmt:
                        st.success("✅ ข้อมูลครบถ้วน พร้อมพิมพ์")
                        btn_type = "primary" # สีแดง/ส้ม
                        btn_label = "🖨️ พิมพ์เอกสาร (PDF)"
                    else:
                        st.info("ℹ️ ยังไม่มีการบันทึกผล (พิมพ์แบบฟอร์มเปล่า)")
                        btn_type = "secondary" # สีปกติ
                        btn_label = "🖨️ พิมพ์แบบฟอร์มเปล่า"

                    if isinstance(pdf_bytes, (bytes, bytearray)):
                        st.download_button(
                            label=btn_label,
                            data=bytes(pdf_bytes),
                            file_name=f"Report_{sid}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type=btn_type
                        )

            else:
                st.error("ไม่พบข้อมูล"); st.button("กลับ", on_click=back_to_list)
    except Exception as e: st.error(f"Error: {e}")

# --- 6. หน้าแจ้งเหตุ ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5]); c2.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"): st.session_state.submitted_id = None; st.rerun()
    else:
        with st.form("report"):
            c1, c2 = st.columns(2)
            with c1: rep = st.text_input("ชื่อผู้แจ้ง *"); typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            with c2: loc = st.text_input("สถานที่เกิดเหตุ *"); img = st.file_uploader("รูปภาพ (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
            det = st.text_area("รายละเอียด *")
            if st.form_submit_button("ส่งข้อมูล", use_container_width=True):
                if rep and typ and loc and det:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    img_b64 = ""
                    if img:
                        try:
                            im = Image.open(img); im.thumbnail((400, 400)); buf = io.BytesIO()
                            im.save(buf, format="JPEG"); img_b64 = base64.b64encode(buf.getvalue()).decode()
                        except: pass
                    df_old = conn.read(ttl=0)
                    new_r = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": img_b64}])
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
