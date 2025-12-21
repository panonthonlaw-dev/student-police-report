import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random
from fpdf import FPDF # เพิ่มการนำเข้า FPDF

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบสารวัตรนักเรียน", page_icon="👮‍♂️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .stDeployButton {display:none;} [data-testid="stSidebar"] {display: none;}
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .success-msg { padding: 10px; background-color: #dcfce7; border-left: 5px solid #15803d; color: #14532d; border-radius: 5px; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔑 2. ข้อมูลเจ้าหน้าที่ ---
OFFICER_ACCOUNTS = {
    "Patwit1510": {"name": "แอดมินสูงสุด", "role": "admin"},
    "Pencharee001": {"name": "ครูเพ็ญชรีย์ (ปกครอง)", "role": "admin"},
    "Chaiya001": {"name": "ครูไชยา (ปกครอง)", "role": "admin"},
    "Jak001": {"name": "ยามจักร (รปภ.)", "role": "admin"},
    "User01": {"name": "ผู้กำกับ (ตำรวจนักเรียน)", "role": "admin"},
    "User02": {"name": "รองผู้กำกับจราจร (ตำรวจนักเรียน)", "role": "admin"},
    "User03": {"name": "ครูเวร (ตรวจการณ์)", "role": "viewer"},
    "User04": {"name": "ตำรวจนักเรียน", "role": "viewer"}
}

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# ฟังก์ชันสร้าง PDF (รองรับภาษาไทย)
def create_pdf(row_data):
    pdf = FPDF()
    pdf.add_page()
    
    # พยายามโหลดฟอนต์ไทย (คุณครูต้องมีไฟล์ fonts/THSarabunNew.ttf ใน GitHub)
    try:
        pdf.add_font('THSarabun', '', 'fonts/THSarabunNew.ttf')
        pdf.set_font('THSarabun', '', 16)
    except:
        pdf.set_font('Arial', '', 12) # ถ้าไม่มีฟอนต์ไทยจะใช้ Arial แทน (แต่อ่านไทยไม่ออก)

    pdf.cell(200, 10, txt="ใบสรุปการดำเนินการ - สารวัตรนักเรียน", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"เลขที่รับแจ้ง: {row_data['Report_ID']}", ln=True)
    pdf.cell(200, 10, txt=f"วันเวลาแจ้ง: {row_data['Timestamp']}", ln=True)
    pdf.cell(200, 10, txt=f"ประเภทเหตุ: {row_data['Incident_Type']}", ln=True)
    pdf.cell(200, 10, txt=f"สถานที่: {row_data['Location']}", ln=True)
    pdf.multi_cell(0, 10, txt=f"รายละเอียดเหตุ: {row_data['Details']}")
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"สถานะปัจจุบัน: {row_data['Status']}", ln=True)
    pdf.multi_cell(0, 10, txt=f"บันทึกการจัดการ: {row_data['Action_Details']}")
    pdf.cell(200, 10, txt=f"ผู้รับผิดชอบ: {row_data['Handled_By']}", ln=True)
    
    return pdf.output()

# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ ---
def officer_dashboard():
    user = st.session_state.current_user
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='main-header'>🏢 ระบบจัดการเหตุการณ์ ({user['name']})</div>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🔴 ออกจากระบบ", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            st.info("ยังไม่มีข้อมูลในระบบ")
            return

        tab1, tab2 = st.tabs(["🔎 ตารางข้อมูล", "🛠 ดำเนินการ/พิมพ์เอกสาร"])

        with tab1:
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                report_list = df['Report_ID'].dropna().unique().tolist()
                selected_id = st.selectbox("เลือกเลขที่รับแจ้ง", report_list)
                selection = df[df['Report_ID'] == selected_id]
                
                if not selection.empty:
                    row_idx = selection.index[0]
                    row_data = selection.iloc[0]

                    with st.container(border=True):
                        st.markdown(f"📦 **จัดการเลขที่:** {selected_id}")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            new_status = st.selectbox("สถานะ", ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"], 
                                                   index=["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"].index(row_data['Status']) if row_data['Status'] in ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"] else 0)
                        with col_b:
                            st.write(f"✍️ **ผู้ดำเนินการ:** {user['name']}")
                        
                        action_detail = st.text_area("บันทึกรายละเอียดการจัดการ", value=row_data['Action_Details'] if pd.notna(row_data['Action_Details']) else "")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾 บันทึกข้อมูล", type="primary", use_container_width=True):
                                df.at[row_idx, 'Status'] = new_status
                                df.at[row_idx, 'Action_Details'] = action_detail
                                df.at[row_idx, 'Handled_By'] = user['name']
                                conn.update(data=df)
                                st.markdown("<div class='success-msg'>✅ ระบบบันทึกการเปลี่ยนแปลงเรียบร้อยแล้ว!</div>", unsafe_allow_html=True)
                                st.toast("บันทึกสำเร็จ!")
                        
                        with col_btn2:
                            # ปุ่มปริ้น PDF
                            pdf_data = create_pdf(row_data)
                            st.download_button(
                                label="📥 ดาวน์โหลดไฟล์ PDF (พิมพ์เอกสาร)",
                                data=bytes(pdf_data),
                                file_name=f"Report_{selected_id}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
            else:
                st.warning("🔒 สิทธิ์ของคุณดูข้อมูลได้อย่างเดียว")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 📝 4. หน้าจอหลัก (แจ้งเหตุ) ---
def main_page():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>👮‍♂️ แจ้งเหตุสารวัตรนักเรียน</h1>", unsafe_allow_html=True)
    
    if st.session_state.get('submitted_id'):
        st.success(f"ส่งข้อมูลสำเร็จ! เลขรับแจ้งของคุณคือ: {st.session_state.submitted_id}")
        if st.button("แจ้งเหตุใหม่"):
            st.session_state.submitted_id = None
            st.rerun()
    else:
        with st.form("report"):
            rep = st.text_input("ชื่อผู้แจ้ง")
            typ = st.selectbox("ประเภท", ["ทะเลาะวิวาท", "สารเสพติด", "ชู้สาว", "หนีเรียน", "อื่นๆ"])
            loc = st.text_input("สถานที่ *")
            det = st.text_area("รายละเอียด *")
            if st.form_submit_button("ส่งข้อมูล"):
                if loc and det:
                    rid = f"POL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                    df_old = conn.read(ttl=0)
                    new_row = pd.DataFrame([{"Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Reporter": rep, "Incident_Type": typ, "Location": loc, "Details": det, "Status": "รอดำเนินการ", "Action_Details": "", "Handled_By": "", "Report_ID": rid}])
                    conn.update(data=pd.concat([df_old, new_row], ignore_index=True))
                    st.session_state.submitted_id = rid
                    st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔐 เจ้าหน้าที่"):
        pw = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pw in OFFICER_ACCOUNTS:
                st.session_state.current_user = OFFICER_ACCOUNTS[pw]
                st.rerun()

if st.session_state.current_user:
    officer_dashboard()
else:
    main_page()
