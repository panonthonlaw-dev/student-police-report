# --- 📋 3. หน้าจอ Dashboard เจ้าหน้าที่ (ฉบับแก้ไข Error) ---
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
        
        # ตรวจสอบว่ามีข้อมูลในตารางหรือไม่
        if df is None or df.empty:
            st.warning("⚠️ ขณะนี้ยังไม่มีข้อมูลการแจ้งเหตุในระบบ")
            return

        # สรุปยอด
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ทั้งหมด", len(df))
        m2.metric("🔴 รอดำเนินการ", len(df[df['Status'] == 'รอดำเนินการ']) if 'Status' in df.columns else 0)
        m3.metric("🟡 กำลังจัดการ", len(df[df['Status'] == 'กำลังจัดการ']) if 'Status' in df.columns else 0)
        m4.metric("🟢 จัดการแล้ว", len(df[df['Status'] == 'จัดการแล้ว']) if 'Status' in df.columns else 0)

        tab1, tab2 = st.tabs(["🔎 ตารางจัดการเหตุ", "🛠 อัปเดตการดำเนินงาน"])

        with tab1:
            st.subheader("ฐานข้อมูลเหตุการณ์ (เรียงจากล่าสุด)")
            st.dataframe(df.iloc[::-1], use_container_width=True)

        with tab2:
            if user['role'] == 'admin':
                with st.container(border=True):
                    # ตรวจสอบว่ามีคอลัมน์ Report_ID หรือไม่
                    if 'Report_ID' in df.columns:
                        report_list = df['Report_ID'].dropna().unique().tolist()
                        if report_list:
                            selected_id = st.selectbox("เลือกเลขที่รับแจ้งที่ต้องการจัดการ", report_list)
                            
                            # ดึงข้อมูลแถวที่เลือกแบบปลอดภัย
                            selection = df[df['Report_ID'] == selected_id]
                            
                            if not selection.empty:
                                row_data = selection.iloc[0]
                                row_idx = selection.index[0]

                                st.markdown(f"**เหตุการณ์:** {row_data['Incident_Type']} | **สถานที่:** {row_data['Location']}")
                                st.write(f"**รายละเอียด:** {row_data['Details']}")
                                
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    status_options = ["รอดำเนินการ", "กำลังจัดการ", "จัดการแล้ว", "ยกเลิก"]
                                    current_status = row_data['Status'] if row_data['Status'] in status_options else "รอดำเนินการ"
                                    new_status = st.selectbox("สถานะการดำเนินงาน", status_options, index=status_options.index(current_status))
                                with col_b:
                                    st.text_input("เจ้าหน้าที่ผู้รับผิดชอบ", value=user['name'], disabled=True)
                                
                                action_detail = st.text_area("บันทึกรายละเอียดการจัดการ", value=row_data['Action_Details'] if pd.notna(row_data['Action_Details']) else "")

                                if st.button("💾 บันทึกการดำเนินงาน", type="primary", use_container_width=True):
                                    df.at[row_idx, 'Status'] = new_status
                                    df.at[row_idx, 'Action_Details'] = action_detail
                                    df.at[row_idx, 'Handled_By'] = user['name']
                                    update_db(df)
                            else:
                                st.error("ไม่พบข้อมูลของเลขรับแจ้งนี้")
                        else:
                            st.info("ยังไม่มีเลขที่รับแจ้งในระบบ")
                    else:
                        st.error("❌ ไม่พบคอลัมน์ 'Report_ID' ใน Google Sheets กรุณาเพิ่มหัวตารางใน Column I")
            else:
                st.warning("🔒 คุณมีสิทธิ์ชมเท่านั้น")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
