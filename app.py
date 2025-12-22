# --- แก้ไขจุดที่ 1: ปรับปรุงฟังก์ชันย่อรูป (ให้เบาเครื่อง เก็บได้นาน) ---
def process_image(img_file):
    if img_file is None: return ""
    try:
        from PIL import Image
        img = Image.open(img_file)
        
        # แปลงโหมดสีให้เป็น RGB เสมอ (กัน Error เวลาเจอไฟล์ png แบบโปร่งใส)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
            
        # ย่อขนาดรูป: ให้ด้านที่ยาวที่สุดไม่เกิน 800px (ชัดพอสำหรับหลักฐาน แต่ไฟล์เล็ก)
        img.thumbnail((800, 800)) 
        
        buffer = io.BytesIO()
        # บันทึกเป็น JPEG และลดคุณภาพลงเหลือ 65% (ตาเปล่ามองไม่ต่าง แต่ไฟล์เล็กลง 5-10 เท่า)
        img.save(buffer, format="JPEG", quality=65, optimize=True)
        
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""
