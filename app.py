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

# --- 2. ระบบจัดการ State (ตัวแปรจำค่า) ---
# ต้องประกาศฟังก์ชัน Callback ก่อนใช้งาน
def view_case(rid):
    """ฟังก์ชันสำหรับกดปุ่มแล้วไปหน้าสอบสวนทันที"""
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"

def back_to_list():
    """ฟังก์ชันสำหรับกดปุ่มย้อนกลับ"""
    st.session_state.view_mode = "list"
    st.session_state.selected_case_id = None

# ประกาศค่าเริ่มต้น
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
    
    /* ปรับแต่งปุ่มให้เต็มช่อง */
    div[data-testid="column"] button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def clean_val(val):
    if pd.isna(val) or str(val).lower() == "nan" or str(val) == "": return ""
    return str(val)

# --- 🔑 3. ข้อมูลบัญชีและระบบสิทธิ์ ---
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

# เช็ค Timeout 30 นาที
if st.session_state.current_user:
    elapsed = (get_now_th() - st.session_state.last_activity).total_seconds()
    if elapsed > 1800:
        st.session_state.current_user = None
        st.session_state.view_mode = "list"
        st.rerun()
    else:
        st.session_state.last_activity = get_now_th()

# --- 📄 4. ฟังก์ชันสร้าง PDF ---
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
        pdf.cell(90, 8, txt=f"เลขที่รับแจ้ง: {row_data.get('Report_ID', '-')}")
        pdf.cell(90, 8, txt=f"วันที่แจ้งเหตุ: {row_data.get('Timestamp', '-')}", align='R', ln=True)
        pdf.ln(5)
        pdf.multi_cell(0, 8, txt=f"ประเภทเหตุ: {row_data.get('Incident_Type', '-')} | สถานที่: {row_data.get('Location', '-')}")
        pdf.multi_cell(0, 8, txt=f"รายละเอียดเหตุการณ์เดิม: {row_data.get('Details', '-')}")
        
        pdf.ln(5); pdf.set_font('ThaiFont', '', 15); pdf.cell(0, 8, txt="ผลการดำเนินการสอบสวน:", ln=True)
        pdf.set_font('ThaiFont', '', 14); pdf.multi_cell(0, 8, txt=clean_val(row_data.get('Statement')), border=1)
        
        pdf.ln(10); pdf.set_font('ThaiFont', '', 14)
        # ลายเซ็น 5 ฝ่าย
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

# --- 📋 5. หน้าจอ Dashboard เจ้าหน้าที่ ---
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
        
        # *** แก้ไขสำคัญ: บังคับให้ Report_ID เป็น String เสมอ เพื่อแก้ปัญหาเลขหาย ***
        df['Report_ID'] = df['Report_ID'].astype(str).str.replace('.0', '', regex=False)

        # --- VIEW MODE: LIST (หน้ารายการ) ---
        if st.session_state.view_mode == "list":
            st.info("💡 รายการสีเขียว = จบเคสแล้ว (กดเพื่อโหลด PDF) | รายการปกติ = กดเพื่อเข้าไปสอบสวน")
            
            # หัวตาราง
            c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
            c1.markdown("**เลขที่รับแจ้ง (คลิกปุ่ม)**")
            c2.markdown("**วันเวลา**")
            c3.markdown("**ประเภทเหตุ**")
            c4.markdown("**สถานะ**")
            st.markdown("---")

            # แสดงรายการ
            for index, row in df.iloc[::-1].iterrows():
                rid = row['Report_ID']
                
                # ตรวจสอบว่ามีข้อมูลจริงไหม (ป้องกันแถวว่าง)
                if not rid or rid == "nan": continue

                has_result = clean_val(row.get('Statement')) != ""
                
                cc1, cc2, cc3, cc4 = st.columns([2.5, 2, 3, 1.5])
                
                with cc1:
                    # ถ้ามีผลสอบสวนแล้ว -> ปุ่ม Download PDF (สีเขียว)
                    if has_result:
                        pdf_data = create_pdf(row)
                        if isinstance(pdf_data, (bytes, bytearray)):
                            st.download_button(
                                label=f"📥 {rid} (PDF)",
                                data=bytes(pdf_data),
                                file_name=f"Report_{rid}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary"
                            )
                    # ถ้ายังไม่มีผลสอบสวน -> ปุ่มไปหน้า Detail (ใช้ on_click เพื่อความเสถียร)
                    else:
                        st.button(
                            f"📝 {rid}", 
                            key=f"btn_{rid}_{index}", # ใช้ index ช่วยให้ key ไม่ซ้ำแน่นอน
                            use_container_width=True,
                            on_click=view_case, # เรียกใช้ Callback Function
                            args=(rid,) # ส่ง rid ไปให้ฟังก์ชัน
                        )
                
                with cc2: st.write(row.get('Timestamp', '-'))
                with cc3: st.write(row.get('Incident_Type', '-'))
                with cc4:
                    if has_result:
                        st.markdown(f"<span style='color:green;font-weight:bold'>✅ จบเคสแล้ว</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:orange;font-weight:bold'>⏳ รอสอบสวน</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

        # --- VIEW MODE: DETAIL (หน้าสอบสวน) ---
        elif st.session_state.view_mode == "detail":
            sid = st.session_state.selected_case_id
            
            # กรองหาแถวที่ตรงกับ ID
            sel = df[df['Report_ID'] == sid]
            
            if not sel.empty:
                idx = sel.index[0]
                row = sel.iloc[0]
                
                # ปุ่มย้อนกลับใช้ Callback เพื่อความชัวร์
                st.button("⬅️ กลับหน้ารายการ", on_click=back_to_list)

                st.markdown(f"### 📝 สอบสวนเคส: {sid}")
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
                    st.write("#### ✍️ บันทึกผลการสอบสวน")
                    
                    f1, f2 = st.columns(2)
                    with f1:
                        v_vic = st.text_input("ผู้เสียหาย *", value=clean_val(row.get('Victim')), disabled=not is_admin)
                        v_acc = st.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row.get('Accused')), disabled=not is_admin)
                        v_wit = st.text_input("พยาน *", value=clean_val(row.get('Witness')), disabled=not is_admin)
                    with f2:
                        v_tea = st.text_input("ครูผู้สอบสวน *", value=clean_val(row.get('Teacher_Investigator')), disabled=not is_admin)
                        v_stu = st.text_input("ตำรวจนักเรียนสอบสวน *", value=clean_val(row.get('Student_Police_Investigator')), disabled=not is_admin)
                        
                        current_status = row.get('Status', 'รอดำเนินการ')
                        opts = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                        # ป้องกัน Error กรณีสถานะเดิมไม่อยู่ในตัวเลือก
                        idx_status = opts.index(current_status) if current_status in opts else 0
                        v_sta = st.selectbox("สถานะ", opts, index=idx_status, disabled=not is_admin)
                    
                    v_stmt = st.text_area("บันทึกคำให้การ/ผลการดำเนินการ *", value=clean_val(row.get('Statement')), disabled=not is_admin)

                    if is_admin:
                        is_complete = all([v_vic, v_acc, v_wit, v_tea, v_stu, v_stmt])
                        if st.button("💾 บันทึกข้อมูลการสอบสวน", type="primary", use_container_width=True, disabled=not is_complete):
                            df.at[idx, 'Victim'] = v_vic
                            df.at[idx, 'Accused'] = v_acc
                            df.at[idx, 'Witness'] = v_wit
                            df.at[idx, 'Teacher_Investigator'] = v_tea
                            df.at[idx, 'Student_Police_Investigator'] = v_stu
                            df.at[idx, 'Status'] = v_sta
                            df.at[idx, 'Statement'] = v_stmt
                            df.at[idx, 'Handled_By'] = user['name']
                            conn.update(data=df)
                            
                            st.toast("✅ บันทึกข้อมูลเรียบร้อยแล้ว!", icon="💾")
                            st.success("✅ บันทึกข้อมูลการสอบสวนลงระบบเรียบร้อยแล้ว!")
                            time.sleep(2)
                            # กลับหน้าหลักด้วยการเซ็ต state แล้ว rerun
                            st.session_state.view_mode = "list"
                            st.rerun()
                            
                        if not is_complete:
                            st.caption("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบทุกช่อง เพื่อเปิดใช้งานปุ่มบันทึก")
            else:
                st.error("ไม่พบข้อมูลเคสนี้ (อาจถูกลบไปแล้ว)")
                if st.button("กลับ"): back_to_list()

    except Exception as e: st.error(f"Error: {e}")

# --- 📝 6. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    if os.path.exists(LOGO_FILE):
        c1, c2, c3 = st.columns([5, 1, 5])
        with c2: st.image(LOGO_FILE, width=100)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.submitted_id:
        st.markdown(f"<div class='report-id-box'><h2>ส่งข้อมูลสำเร็จ!</h2><p>เลขรับแจ้ง: <b>{st.session_state.submitted_id}</b></p></div>", unsafe_allow_html=True)
        if st.button("แจ้งเรื่องใหม่"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.form("report_form"):
            st.info("กรุณากรอกข้อมูลฟิลด์บังคับ (*) ให้ครบถ้วน")
            c1, c2 = st.columns(2)
            with c1:
                rep = st.text_input("ชื่อผู้แจ้ง *")
                typ = st.selectbox("ประเภทเหตุ *", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            with c2:
                loc = st.text_input("สถานที่เกิดเหตุ *")
                img_file = st.file_uploader("แนบรูปภาพเหตุการณ์ (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
            det = st.text_area("รายละเอียดเหตุการณ์")
            
            if st.form_submit_button("📤 ส่งข้อมูลแจ้งเหตุ", use_container_width=True):
                if rep and typ and loc:
                    rid = f"POL-{get_now_th().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    img_b64 = ""
                    if img_file:
                        try:
                            image = Image.open(img_file); image.thumbnail((400, 400))
                            buffer = io.BytesIO(); image.save(buffer, format="JPEG", quality=70)
                            img_b64 = base64.b64encode(buffer.getvalue()).decode()
                        except: pass

                    df_old = conn.read(ttl=0)
                    new_r = pd.DataFrame([{"Timestamp": get_now_th().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Report_ID": rid, "Image_Data": img_b64}])
                    conn.update(data=pd.concat([df_old, new_r], ignore_index=True))
                    st.session_state.submitted_id = rid
                    st.rerun()
                else: st.error("⚠️ กรุณากรอกชื่อผู้แจ้ง, สถานที่ และประเภทเหตุให้ครบถ้วน")

    st.markdown("---")
    with st.expander("🔐 สำหรับเจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.session_state.last_activity = get_now_th()
                st.rerun()
            else: st.error("❌ รหัสผ่านไม่ถูกต้อง")

# --- 🚀 7. รันระบบ ---
if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
