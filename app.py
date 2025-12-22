import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz, random, os, base64, io, qrcode, glob, math, json, requests, re, textwrap, time
from PIL import Image

# PDF Libraries
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except: pass

# ==========================================
# 1. INITIAL SETTINGS & SESSION STATE
# ==========================================
st.set_page_config(page_title="ระบบเจ้าหน้าที่ส่วนกลาง", page_icon="👮‍♂️", layout="wide")

# สร้าง Session State ให้ครบถ้วน
states = {
    'logged_in': False, 'user_info': {}, 'current_dept': None,
    'view_mode': 'list', 'selected_case_id': None, 'unlock_password': "",
    'page_pending': 1, 'page_finished': 1, 'search_query_main': ""
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "THSarabunNew.ttf")

# --- ระบบค้นหาโลโก้ ---
LOGO_PATH = next((f for f in glob.glob(os.path.join(BASE_DIR, "school_logo*")) if os.path.isfile(f)), None)
def get_base64_image(path):
    if not path or not os.path.exists(path): return ""
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')
LOGO_BASE64 = get_base64_image(LOGO_PATH)

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
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=65, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

def view_case(rid):
    st.session_state.selected_case_id = rid
    st.session_state.view_mode = "detail"
    st.session_state.unlock_password = ""

# ==========================================
# 3. PDF SYSTEM (ลายเซ็น 5 คน + Footer ครบ)
# ==========================================
def create_pdf(row):
    rid = str(row.get('Report_ID', ''))
    qr = qrcode.make(rid)
    qi = io.BytesIO(); qr.save(qi, format="PNG")
    qr_b64 = base64.b64encode(qi.getvalue()).decode()
    
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

    p_name = st.session_state.user_info.get('name', 'System')
    p_time = get_now_th().strftime("%d/%m/%Y %H:%M:%S")
    logo_html = f'<img class="logo" src="data:image/png;base64,{LOGO_BASE64}">' if LOGO_BASE64 else ""

    img_html = ""
    for k in ['Image_Data', 'Evidence_Image']:
        if clean_val(row.get(k)):
            img_html += f'<div style="text-align:center;margin-top:10px;"><img src="data:image/jpeg;base64,{row[k]}" style="max-width:380px; max-height:250px; object-fit:contain; border:1px solid #ccc;"></div>'

    html_content = f"""
    <html>
    <head>
        <style>
            @font-face {{ font-family: 'THSarabunNew'; src: url('file://{FONT_FILE}'); }}
            @page {{
                size: A4; margin: 2cm;
                @bottom-right {{ content: "ผู้พิมพ์: {p_name} | เวลา: {p_time} | หน้า " counter(page); font-family: 'THSarabunNew'; font-size: 12pt; }}
            }}
            body {{ font-family: 'THSarabunNew'; font-size: 16pt; line-height: 1.3; }}
            .header {{ text-align: center; position: relative; min-height: 100px; }}
            .logo {{ position: absolute; top: 0; left: 0; width: 60px; }}
            .qr {{ position: absolute; top: 0; right: 0; width: 60px; }}
            .box {{ border: 1px solid #000; padding: 10px; margin-bottom: 10px; min-height: 80px; white-space: pre-wrap; background: #f9f9f9; }}
            .sig-table {{ width: 100%; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            {logo_html}
            <div style="font-size: 22pt; font-weight: bold;">สถานีตำรวจภูธรโรงเรียนโพนทองพัฒนาวิทยา</div>
            <div style="font-size: 18pt;">ใบสรุปรายงานเหตุการณ์และผลการดำเนินการสอบสวน</div>
            <img class="qr" src="data:image/png;base64,{qr_base64}">
        </div>
        <hr>
        <table style="width:100%;">
            <tr>
                <td><b>เลขที่รับแจ้ง:</b> {rid}</td>
                <td style="text-align:right;"><b>วันที่แจ้ง:</b> {row.get('Timestamp','-')}<br><b>วันที่บันทึกผล:</b> {latest_date}</td>
            </tr>
        </table>
        <p><b>ผู้แจ้ง:</b> {row.get('Reporter','-')} | <b>ประเภทเหตุ:</b> {row.get('Incident_Type','-')} | <b>สถานที่:</b> {row.get('Location','-')}</p>
        <p><b>รายละเอียดเหตุการณ์:</b></p><div class="box">{row.get('Details','-')}</div>
        <p><b>ผลการดำเนินการสอบสวน:</b></p><div class="box">{row.get('Statement','-')}</div>
        {img_html}
        <table class="sig-table">
            <tr>
                <td width="50%">ลงชื่อ..........................................................<br>( {row.get('Victim','')} )<br>ผู้เสียหาย</td>
                <td width="50%">ลงชื่อ..........................................................<br>( {row.get('Accused','')} )<br>ผู้ถูกกล่าวหา</td>
            </tr>
            <tr>
                <td>ลงชื่อ..........................................................<br>( {row.get('Student_Police_Investigator','')} )<br>ตำรวจนักเรียนผู้สอบสวน</td>
                <td>ลงชื่อ..........................................................<br>( {row.get('Witness','')} )<br>พยาน</td>
            </tr>
            <tr>
                <td colspan="2"><br>ลงชื่อ..........................................................<br>( {row.get('Teacher_Investigator','')} )<br>ครูผู้สอบสวน</td>
            </tr>
        </table>
    </body>
    </html>
    """
    return HTML(string=html_content, base_url=BASE_DIR).write_pdf(font_config=FontConfiguration())

# ==========================================
# 4. MODULE: INVESTIGATION
# ==========================================
def investigation_module():
    user = st.session_state.user_info
    st.sidebar.button("⬅️ กลับหน้าเลือกแผนก", on_click=lambda: st.session_state.update({'current_dept': None, 'view_mode': 'list'}), width='stretch')
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_raw = conn.read(ttl="0")
        df_display = safe_ensure_columns_for_view(df_raw.copy()).fillna("")
        df_display['Report_ID'] = df_display['Report_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        if st.session_state.view_mode == "list":
            col_h1, col_h2 = st.columns([4, 1])
            col_h1.markdown(f"### 🏢 ระบบสอบสวน คุณ{user['name']}")
            if col_h2.button("🔴 Logout", use_container_width=True):
                st.session_state.clear(); st.rerun()

            tab_list, tab_dash = st.tabs(["📋 รายการแจ้งเหตุ", "📊 แดชบอร์ดสถิติ"])
            
            with tab_list:
                # ระบบค้นหา
                search_q = st.text_input("🔍 ค้นหา", placeholder="เลขเคส, ชื่อ, หรือเหตุการณ์...", key="inv_search_box")
                filtered = df_display.copy()
                if search_q:
                    filtered = filtered[filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]
                
                # แยก Pending และ Finished
                df_p = filtered[filtered['Status'].isin(["รอดำเนินการ", "อยู่ระหว่างการดำเนินการ"])][::-1]
                df_f = filtered[filtered['Status'] == "ดำเนินการเรียบร้อย"][::-1]

                # --- ⏳ รายการที่รอ ---
                st.markdown("<h4 style='color:#1E3A8A; background-color:#f0f2f6; padding:10px; border-radius:5px;'>⏳ รายการที่รอการดำเนินการ</h4>", unsafe_allow_html=True)
                start, end, cur, tot = calculate_pagination('page_pending', len(df_p))
                for idx, row in df_p.iloc[start:end].iterrows():
                    c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
                    with c1: st.button(f"📝 {row['Report_ID']}", key=f"p_{idx}", use_container_width=True, on_click=view_case, args=(row['Report_ID'],))
                    c2.write(row['Timestamp']); c3.write(row['Incident_Type']); c4.write("⏳ รอ")
                    st.divider()

                # --- ✅ รายการที่เรียบร้อย (มั่นใจว่าแสดงผล) ---
                st.markdown("<h4 style='color:#2e7d32; background-color:#e8f5e9; padding:10px; border-radius:5px;'>✅ รายการที่ดำเนินการเรียบร้อย</h4>", unsafe_allow_html=True)
                if df_f.empty: st.caption("ไม่มีรายการที่เรียบร้อย")
                else:
                    start_f, end_f, cur_f, tot_f = calculate_pagination('page_finished', len(df_f))
                    for idx, row in df_f.iloc[start_f:end_f].iterrows():
                        c1, c2, c3, c4 = st.columns([2.5, 2, 3, 1.5])
                        with c1: st.button(f"✅ {row['Report_ID']}", key=f"f_{idx}", use_container_width=True, on_click=view_case, args=(row['Report_ID'],))
                        c2.write(row['Timestamp']); c3.write(row['Incident_Type']); c4.write("✅ จบ")
                        st.divider()

        elif st.session_state.view_mode == "detail":
            st.button("⬅️ กลับหน้ารายการ", on_click=lambda: st.session_state.update({'view_mode': 'list', 'unlock_password': ""}), use_container_width=True)
            sid = st.session_state.selected_case_id
            sel = df_display[df_display['Report_ID'] == sid]
            
            if not sel.empty:
                idx_raw = sel.index[0]; row = sel.iloc[0]
                st.markdown(f"### 📝 เลขที่รับแจ้ง: {sid}")
                with st.container(border=True):
                    st.write(f"**ผู้แจ้ง:** {row['Reporter']} | **สถานที่:** {row['Location']}")
                    st.info(f"**รายละเอียด:** {row['Details']}")
                    # ดึงรูปภาพจาก Image_Data
                    if clean_val(row['Image_Data']):
                        st.image(base64.b64decode(row['Image_Data']), width=500, caption="รูปจากผู้แจ้ง")

                is_admin = user.get('role') == 'admin'
                cur_sta = clean_val(row['Status'])
                is_lock = (cur_sta == "ดำเนินการเรียบร้อย" and st.session_state.unlock_password != "Patwit1510")
                if not is_admin: is_lock = True

                if is_lock and cur_sta == "ดำเนินการเรียบร้อย" and is_admin:
                    st.error("🔒 เคสนี้เรียบร้อยแล้ว ใส่รหัส Patwit1510 เพื่อแก้ไข")
                    pwd = st.text_input("รหัสปลดล็อก", type="password")
                    if st.button("ยืนยันปลดล็อก"):
                        if pwd == "Patwit1510": st.session_state.unlock_password = "Patwit1510"; st.rerun()

                with st.form("full_edit_form"):
                    c1, c2 = st.columns(2)
                    v_vic = c1.text_input("ผู้เสียหาย *", value=clean_val(row['Victim']), disabled=is_lock)
                    v_acc = c2.text_input("ผู้ถูกกล่าวหา *", value=clean_val(row['Accused']), disabled=is_lock)
                    v_wit = c1.text_input("พยาน", value=clean_val(row['Witness']), disabled=is_lock)
                    v_stu = c2.text_input("ตำรวจนักเรียน *", value=clean_val(row['Student_Police_Investigator']), disabled=is_lock)
                    v_tea = c1.text_input("ครูผู้สอบสวน *", value=clean_val(row['Teacher_Investigator']), disabled=is_lock)
                    v_sta = c2.selectbox("สถานะ", ["รอดำเนินการ", "ดำเนินการเรียบร้อย", "ยกเลิก"], index=0, disabled=is_lock)
                    v_stmt = st.text_area("ผลการดำเนินการสอบสวน *", value=clean_val(row['Statement']), disabled=is_lock)
                    ev_img = st.file_uploader("📸 แนบรูปหลักฐานเพิ่ม", type=['jpg','png'], disabled=is_lock)

                    if st.form_submit_button("💾 บันทึกข้อมูล") and not is_lock:
                        df_raw.at[idx_raw, 'Victim'] = v_vic; df_raw.at[idx_raw, 'Accused'] = v_acc
                        df_raw.at[idx_raw, 'Witness'] = v_wit; df_raw.at[idx_raw, 'Student_Police_Investigator'] = v_stu
                        df_raw.at[idx_raw, 'Teacher_Investigator'] = v_tea; df_raw.at[idx_raw, 'Statement'] = v_stmt
                        df_raw.at[idx_raw, 'Status'] = v_sta
                        if ev_img: df_raw.at[idx_raw, 'Evidence_Image'] = process_image(ev_img)
                        df_raw.at[idx_raw, 'Audit_Log'] = f"{clean_val(row['Audit_Log'])}\n[{get_now_th().strftime('%d/%m/%Y %H:%M')}] แก้ไขโดย {user['name']}"
                        conn.update(data=df_raw.fillna("")); st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()

                # ระบบ PDF
                st.divider()
                try:
                    pdf_data = create_pdf(row)
                    st.download_button(label="📥 ดาวน์โหลด PDF (สำนวนคดี)", data=pdf_data, file_name=f"Report_{sid}.pdf", mime="application/pdf", use_container_width=True, type="primary")
                except: st.error("PDF ขัดข้อง")

    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 5. MAIN GATEWAY
# ==========================================
def main():
    if not st.session_state.logged_in:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h2 style='text-align:center;'>👮‍♂️ Central Login</h2>", unsafe_allow_html=True)
                pwd = st.text_input("รหัสผ่านเจ้าหน้าที่", type="password")
                if st.button("เข้าสู่ระบบ", width='stretch', type='primary'):
                    accs = st.secrets.get("OFFICER_ACCOUNTS", {})
                    if pwd in accs:
                        st.session_state.logged_in = True; st.session_state.user_info = accs[pwd]; st.rerun()
                    else: st.error("❌ รหัสผิด")
    else:
        if st.session_state.current_dept is None:
            st.title("🏢 เลือกแผนกปฏิบัติงาน")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("🕵️ งานสอบสวน")
                    if st.button("เข้าใช้งานสอบสวน", use_container_width=True, type="primary"):
                        st.session_state.current_dept = "inv"; st.rerun()
            with c2:
                with st.container(border=True):
                    st.subheader("🚦 งานจราจร")
                    if st.button("เข้าใช้งานจราจร", use_container_width=True, type="primary"):
                        st.session_state.current_dept = "tra"; st.rerun()
        else:
            if st.session_state.current_dept == "inv": investigation_module()
            elif st.session_state.current_dept == "tra": 
                st.title("🚦 ระบบจราจร"); st.sidebar.button("⬅️ กลับ", on_click=lambda: st.session_state.update({'current_dept': None}))

if __name__ == "__main__": main()
