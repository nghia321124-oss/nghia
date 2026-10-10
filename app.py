import streamlit as st
import json
import os
import base64
from pathlib import Path
from google import genai
from PIL import Image

NONLA_ICON_PATH = Path(__file__).with_name("non-la.svg")
NONLA_ICON_DATA = base64.b64encode(NONLA_ICON_PATH.read_bytes()).decode("ascii")

# 1. Cấu hình giao diện Web (Thay icon thành nón lá)
st.set_page_config(page_title="Việt Phục Remix", page_icon=str(NONLA_ICON_PATH), layout="wide")

# --- HÀM TẢI VÀ LỌC DỮ LIỆU TỪ DATABASE (JSON) ---
@st.cache_data
def load_database():
    items_db = []
    occasions_db = []
    # Đọc file items__.json nếu có
    if os.path.exists('items__.json'):
        with open('items__.json', 'r', encoding='utf-8') as f:
            items_db = json.load(f)
    # Đọc file occasions.json nếu có
    if os.path.exists('occasions.json'):
        with open('occasions.json', 'r', encoding='utf-8') as f:
            occasions_db = json.load(f)
    return items_db, occasions_db

def loc_du_lieu_cho_ai(su_kien, gioi_tinh, items_db):
    """
    Hàm này lấy dữ liệu của CẢ 4 LOẠI TRANG PHỤC để gửi cho AI.
    """
    if not items_db:
        return "Chưa tải được database, hãy tư vấn bằng kiến thức có sẵn của bạn."
    
    tom_tat = []
    try:
        # Tăng lên lấy 30 dòng đầu tiên (chứa thông tin quan trọng nhất về bối cảnh, lịch sử, dịp mặc)
        for item in items_db[:30]: 
            if isinstance(item, dict):
                # Trích xuất ĐẦY ĐỦ các trường thông tin của cả 4 cột
                ten_truong = item.get("field3", "")
                vp01 = item.get("field6", "") # Áo ngũ thân
                vp02 = item.get("field7", "") # Áo nhật bình
                vp04 = item.get("field8", "") # Áo tứ thân
                vp06 = item.get("field9", "") # Áo dài
                
                # Bỏ qua các dòng trống
                if ten_truong and ten_truong != "STT":
                    tom_tat.append(f"{ten_truong} | Ngũ Thân: {vp01} | Nhật Bình: {vp02} | Tứ Thân: {vp04} | Áo Dài: {vp06}")
    except Exception:
        pass
    
    # Tăng giới hạn lên 6000 ký tự để AI có đủ dữ liệu đọc cả 4 loại trang phục
    chuoi_rut_gon = "\n".join(tom_tat)[:6000] 
    return chuoi_rut_gon

# Tải database vào bộ nhớ (Chỉ chạy 1 lần)
items_db, occasions_db = load_database()

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp, .stApp p, .stApp span, .stApp label, .stMarkdown { color: #2b2b2b !important; }
    .stApp { background-color: #FAEDCD !important; }
    h1, h2, h3 { color: #8B4513 !important; font-family: 'Times New Roman', serif; }
    h1 { text-align: center; border-bottom: 2px dashed #D4A373; padding-bottom: 10px; margin-bottom: 30px !important; }
    .assistant-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin-bottom: 20px;
    }
    .assistant-header img {
        width: 42px;
        height: 42px;
        flex-shrink: 0;
    }
    .assistant-header h1 {
        display: inline-block;
        margin: 0 !important;
        border-bottom: 2px dashed #D4A373;
        padding-bottom: 10px;
    }
    
    [data-testid="stSidebar"] { background-color: #FEFAE0 !important; border-right: 2px solid #D4A373; }
    
    /* Làm trắng nền ô nhập liệu */
    .stSelectbox>div>div, .stTextInput>div>div, .stFileUploader>div>div, .stTextArea>div>div { 
        background-color: #ffffff !important; border: 2px solid #D4A373 !important; border-radius: 8px !important; 
    }
    
    input, textarea, div[data-baseweb="select"] * { color: #2b2b2b !important; }
    ::placeholder { color: #888888 !important; opacity: 1 !important; }
    
    .stButton>button { 
        background-color: #8B4513 !important; border: none !important; border-radius: 8px !important; 
        padding: 10px 20px !important; box-shadow: 4px 4px 0px 0px #D4A373 !important; 
        transition: all 0.2s ease-in-out !important; color: #ffffff !important; font-weight: bold !important;
    }
    .stButton>button:hover { transform: translate(-2px, -2px) !important; box-shadow: 6px 6px 0px 0px #D4A373 !important; background-color: #A0522D !important; }
    
    .outfit-card { background-color: #ffffff; border: 2px solid #343A40; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 5px 5px 0px 0px #D4A373; }
    .info-box { background-color: #FEFAE0; padding: 15px; border-left: 4px solid #8B4513; border-radius: 4px; margin-top: 15px; }
    .warning-box { background-color: #FFE5E5; padding: 15px; border-left: 4px solid #D90429; border-radius: 4px; margin-top: 15px; margin-bottom: 15px; color: #D90429; font-weight: 500;}
    .success-box { background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; border-radius: 4px; margin-bottom: 20px; color: #155724;}
    .analysis-box { background-color: #e2eafc; padding: 15px; border-left: 4px solid #3a86ff; border-radius: 4px; margin-bottom: 20px; color: #03045e; font-style: italic;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f'''
    <div class="assistant-header">
        <img src="data:image/svg+xml;base64,{NONLA_ICON_DATA}" alt="Nón lá Việt Nam" />
        <h1>Trợ lý AI: Việt Phục Remix</h1>
    </div>
    ''',
    unsafe_allow_html=True,
)

# Lấy API key từ bộ nhớ bảo mật của Streamlit
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

col_input, col_output = st.columns([1, 2], gap="large")

with col_input:
    st.subheader("📝 1. Bối cảnh & Nhu cầu")
    
    gioi_tinh = st.radio("Giới tính của bạn:", ["Nam", "Nữ", "Khác"], horizontal=True)
    su_kien = st.text_input("Sự kiện bạn tham gia:", placeholder="Ví dụ: Lễ bảo vệ đồ án, Đi chùa, Đi bar, Tập gym...")
    thoi_tiet = st.text_input("Thời tiết hiện tại:", placeholder="Ví dụ: Nóng 35 độ, Mưa rào, Se lạnh mùa thu...")
    phong_cach = st.radio("Phong cách phối đồ:", ["Truyền thống 100%", "Cách tân hiện đại", "Tự do phá cách (Mix đồ Âu/Sneaker)"])
    mau_sac_yeu_thich = st.text_input("Màu sắc ưu tiên (Tùy chọn):", placeholder="Ví dụ: Đỏ đô, Trắng, Đen...")
    
    st.subheader("📸 2. Stylist Nhìn Dáng")
    uploaded_file = st.file_uploader("Tải ảnh toàn thân của bạn lên", type=["jpg", "jpeg", "png"])
    
    img = None
    if uploaded_file:
        raw_img = Image.open(uploaded_file)
        # Hiển thị ảnh gốc lên web cho đẹp
        st.image(raw_img, caption="Ảnh bạn đã tải lên", use_container_width=True)
        
        # --- BỘ NÉN ẢNH SIÊU TỐC TRÁNH LỖI 503 ---
        # Chuyển đổi sang hệ màu cơ bản và thu nhỏ kích thước tối đa còn 800x800 pixel
        img = raw_img.copy()
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((800, 800)) 
        # Ảnh lúc này chỉ còn khoảng 100-200KB, gửi đi cực mượt!
        
        st.success("Đã nhận ảnh và tối ưu hóa dung lượng! AI sẽ 'soi' dáng của bạn ngay bây giờ.")
    
    submit_btn = st.button("Trổ tài Tư vấn! 🚀", use_container_width=True)

with col_output:
    if submit_btn:
        if not su_kien.strip() or not thoi_tiet.strip():
            st.warning("Vui lòng nhập đầy đủ thông tin Sự kiện và Thời tiết nhé!")
        else:
            with st.spinner("⏳ Stylist đang đọc Database, phân tích ảnh và phối đồ..."):
                try:
                    # Lấy dữ liệu rút gọn từ Database
                    thong_tin_db = loc_du_lieu_cho_ai(su_kien, gioi_tinh, items_db)
                    
                    khuon_mau_json = """
                    Bạn là Stylist kiêm Chuyên gia Văn hóa cho ứng dụng Việt Phục Remix (Giọng điệu Gen Z). 
                    Hãy phân tích Input của người dùng, hình ảnh đính kèm (nếu có), và DỮ LIỆU TỪ DATABASE để tư vấn.
                    
                    BƯỚC 1: PHÂN TÍCH HÌNH ẢNH
                    - Nếu có ảnh, phân tích Tone da và Dáng người. Ghi vào "image_analysis".
                    
                    BƯỚC 2: ĐÁNH GIÁ SỰ KIỆN & THỜI TIẾT
                    - Nếu 'khong_nen' (Đi bar, thể thao, bơi lội...) hoặc thời tiết khắc nghiệt: Đặt "is_suitable": false. Trả về "outfits": [].
                    - Nếu 'rat_hop' / 'hop': Đặt "is_suitable": true. Đề xuất 3 bộ Việt phục RÕ RỆT.
                    - Nếu 'can_nhac': Đặt "is_suitable": true. Đề xuất tối đa 3 bộ, BẮT BUỘC ghi điểm cần lưu ý vào "warnings_vi".
                    
                    TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON CHUẨN SAU (Không chứa thẻ markdown):
                    {
                      "is_suitable": true,
                      "image_analysis": "Phân tích dáng người (hoặc null)",
                      "overall_assessment": "Nhận xét tổng quan giọng Gen Z",
                      "outfits": [
                        {
                          "title": "Tên trang phục",
                          "rationale": "Lý do khuyên mặc",
                          "phu_kien": "Gợi ý phụ kiện đi kèm",
                          "origin": "Bối cảnh lịch sử ra đời",
                          "meaning": "Ý nghĩa văn hóa",
                          "warnings_vi": "Cảnh báo (nếu có, không thì null)"
                        }
                      ]
                    }
                    """
                    
                    # Ghép thông tin người dùng và Dữ liệu DB vào Prompt
                    user_prompt = f"""
                    Giới tính: {gioi_tinh}. Sự kiện: {su_kien}. 
                    Thời tiết: {thoi_tiet}. Phong cách: {phong_cach}. Màu sắc: {mau_sac_yeu_thich}.
                    
                    --- DỮ LIỆU THAM KHẢO TỪ DATABASE ---
                    {thong_tin_db}
                    """
                    
                    prompt_contents = [user_prompt]
                    if img is not None:
                        prompt_contents.append(img)
                    
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt_contents,
                        config=genai.types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type="application/json",
                            system_instruction=khuon_mau_json, 
                        ),
                    )
                    
                    data = json.loads(response.text)
                    is_suitable = data.get("is_suitable", True)
                    image_analysis = data.get("image_analysis")
                    overall_assessment = data.get("overall_assessment", "")
                    outfits = data.get("outfits", [])
                    
                    st.subheader("✨ Gợi ý Styling của bạn")
                    
                    if not is_suitable:
                        st.markdown(f'''<div class="warning-box">
                        <h4 style="margin-top:0; color:#D90429;">🛑 Ải chà chà... Bối cảnh này căng à nha!</h4>
                        {overall_assessment}
                        </div>''', unsafe_allow_html=True)
                        st.info("💡 Khuyên thật lòng: Hãy lưu Việt phục cho một dịp khác trang trọng và phù hợp hơn nhé bro!")
                    else:
                        if image_analysis:
                            st.markdown(f'''<div class="analysis-box"><b>👁️ AI Soi Dáng:</b> {image_analysis}</div>''', unsafe_allow_html=True)
                            
                        st.markdown(f'''<div class="success-box"><b>📝 Nhận xét từ AI:</b> {overall_assessment}</div>''', unsafe_allow_html=True)
                        
                        for idx, outfit in enumerate(outfits):
                            warning_html = ""
                            if outfit.get("warnings_vi"):
                                warning_html = f'''<div class="warning-box"><b>⚠️ Lưu ý sương sương:</b> {outfit.get("warnings_vi")}</div>'''
                            
                            phu_kien = outfit.get("phu_kien", "Không có gợi ý phụ kiện đặc biệt.")
                                
                            html_card = f'''<div class="outfit-card">
<h3>Lựa chọn {idx + 1}: {outfit.get('title', 'Trang phục Việt')}</h3>
<p style="font-size: 16px; font-style: italic;">"{outfit.get('rationale', '')}"</p>
<p style="font-size: 15px; color: #444;"><b>💍 Phụ kiện & Họa tiết:</b> {phu_kien}</p>
{warning_html}
<div class="info-box">
<p style="margin-bottom: 5px;"><b>📜 Bối cảnh ra đời:</b> {outfit.get('origin', 'Đang cập nhật...')}</p>
<p style="margin-bottom: 0;"><b>🌸 Ý nghĩa văn hóa:</b> {outfit.get('meaning', 'Đang cập nhật...')}</p>
</div>
</div>'''
                            st.markdown(html_card, unsafe_allow_html=True)
                        
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "UNAVAILABLE" in error_msg:
                        st.warning("⚠️ Lỗi 503 (Quá tải máy chủ): Hiện tại bộ não AI của Google đang có quá nhiều người truy cập cùng lúc trên toàn thế giới nên phản hồi hơi chậm. Bạn thông cảm đợi khoảng 30 giây rồi bấm nút thử lại nhé!")
                    else:
                        st.error(f"⚠️ Úi, có lỗi nhỏ xảy ra trong quá trình xử lý. Chi tiết: {error_msg}")