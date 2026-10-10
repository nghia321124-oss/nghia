import base64
import io
import json
import os
import re
import time
from html import escape
from pathlib import Path
from typing import List, Optional

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

# =====================================================================
# 1. CẤU HÌNH CHUNG
# =====================================================================
MODEL_NAME = "gemini-3.8-flash"
ICON_PATH = Path(__file__).with_name("non-la.svg")

ICON_DATA = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii") if ICON_PATH.exists() else ""

st.set_page_config(
    page_title="Việt Phục Remix",
    page_icon=str(ICON_PATH) if ICON_PATH.exists() else "👘",
    layout="wide",
)

# =====================================================================
# 2. SYSTEM PROMPT (kiến thức + quy tắc nằm ở đây, không còn database JSON)
# =====================================================================
SYSTEM_PROMPT = """
# VAI TRÒ
Bạn là "Việt Phục Remix Stylist": Stylist Gen Z kiêm Chuyên gia Văn hóa, tư vấn phối trang phục truyền thống Việt Nam cho học sinh, sinh viên. Giọng điệu trẻ trung, thân thiện nhưng không sáo rỗng, luôn tôn trọng giá trị văn hóa. Luôn trả lời bằng tiếng Việt.

# KIẾN THỨC NỀN (làm căn cứ, không bịa thêm)
- Áo dài: biến thể từ áo ngũ thân, định hình hiện đại từ thập niên 1930; hợp lễ lớn, khai giảng, tốt nghiệp, bảo vệ đồ án, Tết, cưới hỏi.
- Áo tứ thân: phổ biến ở Bắc Bộ, 4 mảnh vạt (hai vạt trước buộc lại); hợp lễ hội, hội làng, chụp ảnh văn hóa.
- Áo ngũ thân: áo của tầng lớp bình dân và quan lại thời Nguyễn, có 5 thân (thân phụ nhỏ bên trong); hợp lễ hội, chụp ảnh hoài cổ, sự kiện văn hóa.
- Áo nhật bình: áo của phụ nữ hoàng tộc, cổ vuông, thường thêu họa tiết; hợp sự kiện trang trọng, tái hiện cung đình.
- Các loại khác (áo bà ba, áo giao lĩnh, áo cổ viên lĩnh, khăn đóng, nón quai thao, nón lá, mấn, yếm...): chỉ nói khi chắc chắn về nguồn gốc.

# NGUYÊN TẮC TRUNG THỰC VĂN HÓA (QUAN TRỌNG NHẤT)
1. Không bịa niên đại, nhân vật, địa danh. Nếu không chắc, dùng cách nói thận trọng: "theo nhiều tài liệu", "thường được cho là", "khoảng thế kỷ...".
2. Không gán họa tiết/màu sắc cho một địa phương hay giai cấp nếu không chắc chắn.
3. Phân biệt rõ "Truyền thống chuẩn" và "Cách tân/Remix"; khi remix phải nói rõ phần nào đã được cách tân.
4. Cảnh báo cách phối làm sai lệch đặc trưng văn hóa, ví dụ: trang phục cung đình mặc xuề xòa, dùng họa tiết thiêng liêng/tâm linh làm đồ thời trang tùy tiện, trộn lẫn trang phục các triều đại/vùng miền thiếu hợp lý, nhầm Việt phục với trang phục nước khác.
5. Không tạo nội dung phản cảm hay xúc phạm văn hóa.

# QUY TẮC ĐÁNH GIÁ SỰ KIỆN & THỜI TIẾT
- Rất hợp / Hợp (lễ nghi, văn hóa, học thuật, lễ hội, chụp ảnh, sự kiện trang trọng): is_suitable=true, đề xuất đúng 3 bộ KHÁC NHAU rõ rệt.
- Cần cân nhắc (đông người, đi lại nhiều, thời tiết khó): is_suitable=true, tối đa 3 bộ, BẮT BUỘC ghi điểm cần lưu ý vào warnings_vi.
- Không nên (thể thao, gym, bơi lội, bar/club, mưa to/bão, nắng nóng cực đoan): is_suitable=false, outfits=[]; giải thích ngắn, vui vẻ, không phán xét, gợi ý dịp khác phù hợp hơn.
- Luôn cân nhắc chất liệu theo thời tiết (nóng: lụa mỏng, cotton, linen; lạnh: gấm, nhung, thêm áo khoác ngoài).
- Nếu người dùng chọn địa phương/vùng miền, ưu tiên trang phục và cách mặc gắn với vùng đó nhưng chỉ khi chắc chắn về thông tin.

# QUY TẮC PHỐI ĐỒ
- Cá nhân hóa theo giới tính, sự kiện, địa phương, thời tiết, phong cách và màu ưu tiên.
- "Truyền thống 100%": không pha đồ Âu. "Cách tân hiện đại": cho phép cắt may và chất liệu hiện đại. "Tự do phá cách": cho phép mix sneaker, quần jeans, phụ kiện hiện đại nhưng giữ linh hồn trang phục.
- Màu sắc: mỗi bộ có palette 3-5 màu (tên màu + mã hex #RRGGBB) và giải thích ngắn vì sao hài hòa. Nếu màu người dùng chọn không hợp sự kiện, phải cảnh báo.
- Nếu có ảnh: nhận xét dáng người và tone da tích cực, lịch sự, tập trung vào chọn phom dáng/màu hợp; không chê ngoại hình. Không có ảnh thì image_analysis=null.
- Mỗi trường tối đa 3 câu ngắn gọn.
""".strip()


# =====================================================================
# 3. SCHEMA ĐẦU RA (ép AI trả đúng cấu trúc, không cần "dặn" JSON trong prompt)
# =====================================================================
class ColorSwatch(BaseModel):
    name: str
    hex: str


class Outfit(BaseModel):
    title: str
    outfit_type: str
    authenticity: str  # "Truyền thống chuẩn" hoặc "Cách tân"
    rationale: str
    phu_kien: str
    palette: List[ColorSwatch]
    color_harmony: str
    origin: str
    meaning: str
    warnings_vi: Optional[str] = None


class StylingResult(BaseModel):
    is_suitable: bool
    image_analysis: Optional[str] = None
    overall_assessment: str
    outfits: List[Outfit]


# =====================================================================
# 4. GỌI AI (có cache + retry)
# =====================================================================
def get_api_key():
    """Ưu tiên Streamlit Secrets (khi deploy), nếu không có thì đọc biến môi trường (khi chạy local)."""
    try:
        key = st.secrets["GEMINI_API_KEY"]
        if key:
            return key
    except Exception:  # không có secrets.toml hoặc thiếu key
        pass
    return os.environ.get("GEMINI_API_KEY")


@st.cache_resource
def get_client():
    return genai.Client(api_key=get_api_key())


def build_config(low_thinking: bool) -> types.GenerateContentConfig:
    kwargs = dict(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.6,
        response_mime_type="application/json",
        response_schema=StylingResult,
    )
    if low_thinking:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="low")
    return types.GenerateContentConfig(**kwargs)


def call_model(contents):
    """Gọi model; tự thử lại khi quá tải (503/429); tự bỏ thinking_level nếu model không hỗ trợ."""
    client = get_client()
    low_thinking = True
    last_error = None
    for attempt in range(3):
        try:
            return client.models.generate_content(
                model=MODEL_NAME, contents=contents, config=build_config(low_thinking)
            )
        except Exception as e:  # noqa: BLE001
            last_error = e
            msg = str(e)
            if low_thinking and ("thinking" in msg.lower() or "INVALID_ARGUMENT" in msg):
                low_thinking = False  # thử lại không có thinking_level
                continue
            if any(k in msg for k in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_error


@st.cache_data(show_spinner=False, ttl=3600)
def get_styling(gioi_tinh, su_kien, dia_phuong, thoi_tiet, phong_cach, mau_sac, loai_uu_tien, img_bytes):
    """Cùng một bộ input thì dùng lại kết quả (tiết kiệm token). Lỗi sẽ không bị cache."""
    user_prompt = (
        f"Giới tính: {gioi_tinh}\n"
        f"Sự kiện: {su_kien}\n"
        f"Địa phương/vùng miền: {dia_phuong or 'Không chọn'}\n"
        f"Thời tiết: {thoi_tiet}\n"
        f"Phong cách: {phong_cach}\n"
        f"Màu ưu tiên: {mau_sac or 'Không có'}\n"
        f"Loại trang phục ưu tiên: {', '.join(loai_uu_tien) if loai_uu_tien else 'AI tự chọn'}"
    )
    contents = [user_prompt]
    if img_bytes:
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

    response = call_model(contents)
    data = json.loads(response.text)
    return StylingResult.model_validate(data).model_dump()


def prepare_image(uploaded_file):
    """Nén ảnh còn tối đa 800x800 JPEG để gửi nhanh, nhẹ."""
    img = Image.open(uploaded_file)
    preview = img.copy()
    img = img.convert("RGB")
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return preview, buf.getvalue()


# =====================================================================
# 5. HIỂN THỊ
# =====================================================================
def safe(text) -> str:
    """Escape HTML để nội dung AI không phá giao diện."""
    return escape(str(text)) if text else ""


def safe_hex(value: str) -> str:
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value or "") else "#CCCCCC"


def swatches_html(palette) -> str:
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:2px 10px 2px 0;">'
        f'<span style="width:22px;height:22px;border-radius:50%;background:{safe_hex(c["hex"])};'
        f'border:1px solid #343A40;display:inline-block;margin-right:6px;"></span>{safe(c["name"])}</span>'
        for c in palette
    )
    return f'<div style="margin:8px 0;">{chips}</div>'


def render_outfit_card(idx: int, o: dict):
    badge_color = "#28a745" if o["authenticity"].lower().startswith("truyền thống") else "#3a86ff"
    warning = ""
    if o.get("warnings_vi"):
        warning = f'<div class="warning-box"><b>⚠️ Lưu ý văn hóa:</b> {safe(o["warnings_vi"])}</div>'
    html_card = f"""<div class="outfit-card">
<h3>Lựa chọn {idx}: {safe(o['title'])}</h3>
<span style="background:{badge_color};color:#fff;padding:3px 10px;border-radius:12px;font-size:13px;">{safe(o['authenticity'])}</span>
<span style="margin-left:8px;font-size:13px;color:#666;">{safe(o['outfit_type'])}</span>
<p style="font-size:16px;font-style:italic;margin-top:12px;">"{safe(o['rationale'])}"</p>
<p style="font-size:15px;color:#444;"><b>💍 Phụ kiện:</b> {safe(o['phu_kien'])}</p>
<p style="font-size:15px;color:#444;margin-bottom:0;"><b>🎨 Bảng màu:</b></p>
{swatches_html(o['palette'])}
<p style="font-size:14px;color:#555;"><i>{safe(o['color_harmony'])}</i></p>
{warning}
<div class="info-box">
<p style="margin-bottom:5px;"><b>📜 Nguồn gốc:</b> {safe(o['origin'])}</p>
<p style="margin-bottom:0;"><b>🌸 Ý nghĩa văn hóa:</b> {safe(o['meaning'])}</p>
</div>
</div>"""
    st.markdown(html_card, unsafe_allow_html=True)


def build_lookbook_html(result: dict, ctx: dict) -> str:
    cards = []
    for i, o in enumerate(result["outfits"], 1):
        cards.append(
            f"<div style='border:2px solid #343A40;border-radius:12px;padding:18px;margin:16px 0;background:#fff'>"
            f"<h2 style='color:#8B4513'>Lựa chọn {i}: {safe(o['title'])}</h2>"
            f"<p><b>{safe(o['authenticity'])}</b> · {safe(o['outfit_type'])}</p>"
            f"<p><i>{safe(o['rationale'])}</i></p>"
            f"<p><b>Phụ kiện:</b> {safe(o['phu_kien'])}</p>"
            f"{swatches_html(o['palette'])}"
            f"<p>{safe(o['color_harmony'])}</p>"
            f"<p><b>Nguồn gốc:</b> {safe(o['origin'])}</p>"
            f"<p><b>Ý nghĩa:</b> {safe(o['meaning'])}</p>"
            f"{'<p style=color:#D90429><b>Lưu ý:</b> ' + safe(o['warnings_vi']) + '</p>' if o.get('warnings_vi') else ''}"
            f"</div>"
        )
    return (
        "<html><head><meta charset='utf-8'><title>Lookbook Việt phục</title></head>"
        "<body style='font-family:Georgia,serif;background:#FAEDCD;max-width:760px;margin:auto;padding:20px'>"
        "<h1 style='color:#8B4513;text-align:center'>Lookbook Việt Phục Remix</h1>"
        f"<p style='text-align:center'>Sự kiện: {safe(ctx['su_kien'])} · Thời tiết: {safe(ctx['thoi_tiet'])} · "
        f"Phong cách: {safe(ctx['phong_cach'])}</p>"
        f"{''.join(cards)}</body></html>"
    )


# =====================================================================
# 6. CSS
# =====================================================================
st.markdown(
    """
<style>
    .stApp, .stApp p, .stApp span, .stApp label, .stMarkdown { color: #2b2b2b !important; }
    .stApp { background-color: #FAEDCD !important; }
    h1, h2, h3 { color: #8B4513 !important; font-family: 'Times New Roman', serif; }
    h1 { text-align: center; border-bottom: 2px dashed #D4A373; padding-bottom: 10px; margin-bottom: 30px !important; }
    .assistant-header { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; }
    .assistant-header img { width: 42px; height: 42px; flex-shrink: 0; }
    .assistant-header h1 { display: inline-block; margin: 0 !important; border-bottom: 2px dashed #D4A373; padding-bottom: 10px; }
    [data-testid="stSidebar"] { background-color: #FEFAE0 !important; border-right: 2px solid #D4A373; }
    .stSelectbox>div>div, .stTextInput>div>div, .stFileUploader>div>div, .stTextArea>div>div, .stMultiSelect>div>div {
        background-color: #ffffff !important; border: 2px solid #D4A373 !important; border-radius: 8px !important;
    }
    input, textarea, div[data-baseweb="select"] * { color: #2b2b2b !important; }
    ::placeholder { color: #888888 !important; opacity: 1 !important; }
    .stButton>button, .stDownloadButton>button {
        background-color: #8B4513 !important; border: none !important; border-radius: 8px !important;
        padding: 10px 20px !important; box-shadow: 4px 4px 0px 0px #D4A373 !important;
        transition: all 0.2s ease-in-out !important; color: #ffffff !important; font-weight: bold !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translate(-2px, -2px) !important; box-shadow: 6px 6px 0px 0px #D4A373 !important; background-color: #A0522D !important;
    }
    .outfit-card { background-color: #ffffff; border: 2px solid #343A40; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 5px 5px 0px 0px #D4A373; }
    .info-box { background-color: #FEFAE0; padding: 15px; border-left: 4px solid #8B4513; border-radius: 4px; margin-top: 15px; }
    .warning-box { background-color: #FFE5E5; padding: 15px; border-left: 4px solid #D90429; border-radius: 4px; margin: 15px 0; color: #D90429; font-weight: 500; }
    .success-box { background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; border-radius: 4px; margin-bottom: 20px; color: #155724; }
    .analysis-box { background-color: #e2eafc; padding: 15px; border-left: 4px solid #3a86ff; border-radius: 4px; margin-bottom: 20px; color: #03045e; font-style: italic; }
</style>
""",
    unsafe_allow_html=True,
)

icon_img = f'<img src="data:image/svg+xml;base64,{ICON_DATA}" alt="Nón lá Việt Nam" />' if ICON_DATA else ""
st.markdown(
    f'<div class="assistant-header">{icon_img}<h1>Trợ lý AI: Việt Phục Remix</h1></div>',
    unsafe_allow_html=True,
)
st.caption("Phối trang phục truyền thống Việt Nam theo phong cách Gen Z, vừa hiện đại vừa tôn trọng văn hóa.")

if not get_api_key():
    st.error(
        "Chưa có GEMINI_API_KEY. Chạy local: tạo file .streamlit/secrets.toml cạnh app.py "
        "(nội dung: GEMINI_API_KEY = \"khóa của bạn\"). Khi deploy: thêm vào mục Secrets của Streamlit Cloud."
    )
    st.stop()

# =====================================================================
# 7. GIAO DIỆN
# =====================================================================
LOAI_TRANG_PHUC = ["Áo dài", "Áo tứ thân", "Áo ngũ thân", "Áo nhật bình", "Áo bà ba", "Áo giao lĩnh"]
VUNG_MIEN = ["Không chọn", "Bắc Bộ", "Trung Bộ / Huế", "Nam Bộ", "Tây Nguyên", "Tây Bắc / Đông Bắc"]

col_input, col_output = st.columns([1, 2], gap="large")

with col_input:
    st.subheader("📝 1. Bối cảnh & Nhu cầu")
    gioi_tinh = st.radio("Giới tính của bạn:", ["Nam", "Nữ", "Khác"], horizontal=True)
    su_kien = st.text_input("Sự kiện bạn tham gia:", placeholder="Ví dụ: Lễ bảo vệ đồ án, Đi chùa, Lễ hội làng...")
    dia_phuong = st.selectbox("Địa phương / vùng miền (tùy chọn):", VUNG_MIEN)
    thoi_tiet = st.text_input("Thời tiết hiện tại:", placeholder="Ví dụ: Nóng 35 độ, Mưa rào, Se lạnh...")
    phong_cach = st.radio(
        "Phong cách phối đồ:",
        ["Truyền thống 100%", "Cách tân hiện đại", "Tự do phá cách (Mix đồ Âu/Sneaker)"],
    )
    loai_uu_tien = st.multiselect("Loại trang phục ưu tiên (tùy chọn):", LOAI_TRANG_PHUC)
    mau_sac = st.text_input("Màu sắc ưu tiên (tùy chọn):", placeholder="Ví dụ: Đỏ đô, Trắng, Xanh ngọc...")

    st.subheader("📸 2. Stylist nhìn dáng (tùy chọn)")
    uploaded_file = st.file_uploader("Tải ảnh toàn thân của bạn", type=["jpg", "jpeg", "png"])
    img_bytes = None
    if uploaded_file:
        preview, img_bytes = prepare_image(uploaded_file)
        st.image(preview, caption="Ảnh bạn đã tải lên", width="stretch")

    submit_btn = st.button("Trổ tài Tư vấn! 🚀", width="stretch")

ctx = dict(su_kien=su_kien, thoi_tiet=thoi_tiet, phong_cach=phong_cach)

if submit_btn:
    if not su_kien.strip() or not thoi_tiet.strip():
        st.session_state["error"] = "Vui lòng nhập đầy đủ Sự kiện và Thời tiết nhé!"
        st.session_state.pop("result", None)
    else:
        with col_output:
            with st.spinner("⏳ Stylist đang phân tích và phối đồ..."):
                try:
                    st.session_state["result"] = get_styling(
                        gioi_tinh,
                        su_kien.strip(),
                        "" if dia_phuong == "Không chọn" else dia_phuong,
                        thoi_tiet.strip(),
                        phong_cach,
                        mau_sac.strip(),
                        tuple(loai_uu_tien),
                        img_bytes,
                    )
                    st.session_state["ctx"] = ctx
                    st.session_state.pop("error", None)
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    st.session_state.pop("result", None)
                    if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                        st.session_state["error"] = (
                            "⚠️ Máy chủ AI đang quá tải. Bạn đợi khoảng 30 giây rồi bấm thử lại nhé!"
                        )
                    else:
                        st.session_state["error"] = f"⚠️ Có lỗi xảy ra. Chi tiết: {msg}"

with col_output:
    if st.session_state.get("error"):
        st.warning(st.session_state["error"])

    result = st.session_state.get("result")
    if result:
        st.subheader("✨ Gợi ý Styling của bạn")

        if not result["is_suitable"]:
            st.markdown(
                f'<div class="warning-box"><h4 style="margin-top:0;color:#D90429;">🛑 Bối cảnh này hơi căng nha!</h4>'
                f'{safe(result["overall_assessment"])}</div>',
                unsafe_allow_html=True,
            )
            st.info("💡 Hãy để dành Việt phục cho một dịp phù hợp hơn nhé!")
        else:
            if result.get("image_analysis"):
                st.markdown(
                    f'<div class="analysis-box"><b>👁️ AI soi dáng:</b> {safe(result["image_analysis"])}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div class="success-box"><b>📝 Nhận xét:</b> {safe(result["overall_assessment"])}</div>',
                unsafe_allow_html=True,
            )

            for i, outfit in enumerate(result["outfits"], 1):
                render_outfit_card(i, outfit)

            if len(result["outfits"]) > 1:
                st.subheader("⚖️ So sánh các phương án")
                st.table(
                    [
                        {
                            "Phương án": f"{i}. {o['title']}",
                            "Loại": o["outfit_type"],
                            "Mức độ": o["authenticity"],
                            "Màu chủ đạo": ", ".join(c["name"] for c in o["palette"][:3]),
                        }
                        for i, o in enumerate(result["outfits"], 1)
                    ]
                )

            st.download_button(
                "📥 Tải Lookbook Việt phục (HTML)",
                data=build_lookbook_html(result, st.session_state.get("ctx", ctx)),
                file_name="lookbook_viet_phuc.html",
                mime="text/html",
            )
