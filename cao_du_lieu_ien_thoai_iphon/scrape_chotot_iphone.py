"""
=============================================================
  Cào dữ liệu iPhone từ Chợ Tốt (chotot.com)
  Author : Antigravity (Google DeepMind)
  Version: 3.0  –  cập nhật hàng ngày, xuất Excel + Google Sheets
=============================================================

Các trường được trích xuất:
  1. Phường / Quận / Thành phố
  2. Loại người bán  (Cá nhân / Bán chuyên)
  3. Tình trạng
  4. Hãng & Dòng máy
  5. Phiên bản (lock/quốc tế)
  6. Xuất xứ
  7. Màu sắc
  8. Dung lượng
  9. Chính sách bảo hành
 10. Giá tiền (VNĐ)

Cách dùng:
  python scrape_chotot_iphone.py

Setup Google Sheets:
  Xem file SETUP_GOOGLE_SHEET.md

Lên lịch tự động (Windows Task Scheduler):
  Xem hướng dẫn cuối file.
"""

import re
import requests
import pandas as pd
import json
import time
import os
import logging
from datetime import datetime
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# ──────────────────────────────────────────────
#  CẤU HÌNH
# ──────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent          # thư mục chứa script
OUTPUT_DIR  = BASE_DIR / "output"            # thư mục lưu Excel
LOG_FILE    = BASE_DIR / "scrape_log.txt"    # log file

# Số trang mỗi lần chạy  (mỗi trang 20 tin → 10 trang = 200 tin)
MAX_PAGES   = 10
PAGE_SIZE   = 20
SLEEP_SEC   = 1.2   # nghỉ giữa các request (tránh bị block)

# ── Google Sheets ────────────────────────────────────────────
# 1. Đặt file credentials vào cùng thư mục với script
# 2. Điền Spreadsheet ID lấy từ URL Google Sheet của bạn
# 3. Xem hướng dẫn chi tiết trong SETUP_GOOGLE_SHEET

.md
GSHEET_CREDENTIALS    = BASE_DIR / "google_credentials.json"
GSHEET_SPREADSHEET_ID = "19sLgJdq6XimZhh7Pmv2sbDPQYXfbaEarODgjHwLf5jc"
GSHEET_WORKSHEET_NAME = datetime.now().strftime("%Y-%m-%d")  # tab theo ngày
GSHEET_ENABLED        = GSPREAD_AVAILABLE and GSHEET_CREDENTIALS.exists() and bool(GSHEET_SPREADSHEET_ID)

# Chỉ lấy iPhone (mobile_brand=1 = Apple, cg=5010 = Điện thoại)
# Lọc thêm: mobile_model_name chứa "iPhone 8" trở lên
# Whitelist: chỉ lấy iPhone đời 8 trở lên
# (API đã lọc mobile_brand=1, ta chỉ cần loại thêm các SE cũ/iPhone 7 nếu cần)
IPHONE_MODELS_INCLUDE = [
    "iphone 8", "iphone se", "iphone x",
    "iphone 11", "iphone 12"
    
    , "iphone 13", "iphone 14",
    "iphone 15", "iphone 16", "iphone 17",
]

# ──────────────────────────────────────────────
#  MAPPING MÃ → TÊN TIẾNG VIỆT
#  (Dựa trên phân tích thực tế từ API Chợ Tốt)
# ──────────────────────────────────────────────

ACCOUNT_TYPE_MAP = {
    "s"  : "Cá nhân",
    "b"  : "Bán chuyên",
    True : "Bán chuyên",   # company_ad == True
    False: "Cá nhân",
}

CONDITION_MAP = {
    1: "Mới",
    2: "Đã sử dụng (chưa sửa chữa)",
    3: "Đã sửa chữa / thay linh kiện",
}

LOCK_MAP = {
    1: "Quốc tế (Không khoá mạng)",
    2: "Khóa mạng (Lock)",
    3: "Đã mở khóa",
}

ORIGIN_MAP = {
    1: "Việt Nam",
    2: "Hàn Quốc",
    3: "Trung Quốc",
    4: "Châu Âu",
    5: "Nhật Bản",
    6: "Không rõ",
    7: "Chính hãng VN (VNA)",
    8: "Mỹ (LL/A)",
    9: "Đài Loan",
   10: "Thái Lan",
}

COLOR_MAP = {
    1 : "Đen",
    2 : "Trắng",
    3 : "Xanh dương",
    4 : "Xanh lá",
    5 : "Đỏ",
    6 : "Xám / Space Gray",
    7 : "Vàng",
    8 : "Hồng / Rose Gold",
    9 : "Tím",
    10: "Cam",
    11: "Bạc",
    12: "Xanh Sierra",
    13: "Xanh mòng két",
    14: "Vàng đồng",
    15: "Xanh Pacific",
    16: "Titan Tự nhiên",
    17: "Titan Đen",
    18: "Titan Vàng",
    19: "Titan Trắng / Bạc",
    20: "Hồng nhạt",
    21: "Xanh dương nhạt",
    22: "Vàng nhạt",
    23: "Xanh Desert",
    24: "Đen nhám (Matte Black)",
    25: "Xanh Teal",
}

WARRANTY_MAP = {
    "Hết bảo hành"  : "Hết bảo hành",
    "1 tháng"        : "1 tháng",
    "3 tháng"        : "3 tháng",
    "4-6 tháng"      : "4-6 tháng",
    "7-9 tháng"      : "7-9 tháng",
    "10-12 tháng"    : "10-12 tháng",
    ">12 tháng"      : ">12 tháng",
}

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  HÀM TIỆN ÍCH
# ──────────────────────────────────────────────

def get_param_value(params: list, param_id: str) -> str:
    """Trích value từ mảng params theo id."""
    for p in params:
        if p.get("id") == param_id:
            return p.get("value", "")
    return ""



def map_color(raw_code: int) -> str:
    return COLOR_MAP.get(raw_code, f"Màu khác ({raw_code})")


def map_origin(raw_code: int) -> str:
    return ORIGIN_MAP.get(raw_code, f"Xuất xứ khác ({raw_code})")


def map_lock(raw_code: int) -> str:
    return LOCK_MAP.get(raw_code, "")


def map_condition(raw_code: int) -> str:
    return CONDITION_MAP.get(raw_code, "Không rõ")


# ──────────────────────────────────────────────
#  HÀM XỬ LÝ TÌNH TRẠNG PIN  (3 bước ưu tiên)
# ──────────────────────────────────────────────

def extract_pin(params: list, body: str) -> int | None:
    """
    Trích xuất % pin từ tin đăng.
    Bước 1: Tìm trong params theo label 'Pin' / 'Tình trạng pin'.
    Bước 2: Regex quét body → \d{2,3}% hoặc 'Pin \d{2,3}'.
    Bước 3: Heuristic từ từ khoá mô tả.
    Trả về số nguyên (%) hoặc None nếu không xác định được.
    """
    body_lower = (body or "").lower()

    # ── Bước 1: params có label pin ──────────────────────────────
    PIN_PARAM_IDS = {"pin", "tinh_trang_pin", "battery", "battery_capacity"}
    for p in params:
        label = p.get("label", "").lower()
        pid   = p.get("id", "").lower()
        if "pin" in label or pid in PIN_PARAM_IDS:
            val = str(p.get("value", ""))
            m = re.search(r"(\d{2,3})", val)
            if m:
                num = int(m.group(1))
                if 50 <= num <= 100:
                    return num

    # ── Bước 2: Regex quét body ───────────────────────────────────
    # Khớp: "87%", "pin 87", "87 %", "battery 87"
    patterns = [
        r"pin\s*(\d{2,3})\s*%",          # pin 87%
        r"(\d{2,3})\s*%\s*pin",          # 87% pin
        r"pin\s*(\d{2,3})(?!\s*gb)",     # pin 87 (không phải dung lượng GB)
        r"(\d{2,3})\s*%",               # 87% (tổng quát)
    ]
    for pat in patterns:
        m = re.search(pat, body_lower)
        if m:
            num = int(m.group(1))
            if 50 <= num <= 100:
                return num

    # ── Bước 3: Heuristic theo từ khoá ───────────────────────────
    heuristic_rules = [
        (100, ["mới thay pin", "thay pin mới", "pin 100", "pin zin 100"]),
        (90,  ["pin cao", "pin tốt", "pin đẹp", "99%", "pin 99",
               "pin như mới", "pin trâu", "còn cao"]),
        (75,  ["pin bảo trì", "pin héo", "pin yếu", "pin kém",
               "pin hao", "pin nhanh hết", "pin tụt", "pin cũ"]),
    ]
    for value, keywords in heuristic_rules:
        if any(kw in body_lower for kw in keywords):
            return value

    return None


# ──────────────────────────────────────────────
#  HÀM ĐÁNH GIÁ CHẤT LƯỢNG TỔNG HỢP
# ──────────────────────────────────────────────

# Giá tham chiếu sàn (VNĐ) theo model – dùng cho phát hiện hàng dựng
MODEL_PRICE_FLOOR = {
    "iphone 8"   :  1_500_000,
    "iphone se"  :  1_800_000,
    "iphone x"   :  2_500_000,
    "iphone xr"  :  2_800_000,
    "iphone xs"  :  3_000_000,
    "iphone 11"  :  3_500_000,
    "iphone 12"  :  5_000_000,
    "iphone 13"  :  7_000_000,
    "iphone 14"  :  9_000_000,
    "iphone 15"  : 12_000_000,
    "iphone 16"  : 16_000_000,
}


def _price_floor(model_str: str) -> int:
    """Trả về mức giá sàn cảnh báo cho model tương ứng."""
    ml = model_str.lower()
    for key, floor in MODEL_PRICE_FLOOR.items():
        if key in ml:
            return floor
    return 0


def danh_gia_chat_luong(
    body: str,
    pin_pct: int | None,
    gia: int,
    tinh_trang: str,
    dong_may: str,
) -> str:
    """
    Phân loại chất lượng iPhone: A / B / C / D.

    A – Hoàn hảo  : (99%|likenew) + (zin|chưa sửa)
    B – Khá       : 98% hoặc zin nhưng pin < 85%
    C – Trung bình: trầy xước, pin < 80%, hoặc không đề cập độ zin
    D – Hàng dựng : giá quá rẻ + từ khoá nguy hiểm
    """
    bl = (body or "").lower()
    tl = (tinh_trang or "").lower()

    # ── Từ khoá phân loại ─────────────────────────────────────────
    kw_likenew  = ["99%", "like new", "likenew", "như mới", "nguyên bản"]
    kw_zin      = ["zin", "chưa sửa", "chưa bóc máy", "nguyên zin",
                   "chưa sửa chữa", "full zin"]
    kw_98       = ["98%", "98 %"]
    kw_scratch  = ["trầy", "xước", "móp", "bể", "vỡ", "cong", "lõm"]
    kw_danger   = ["màn mực", "mất face", "bị nứt", "vỡ màn", "hỏng camera",
                   "lỗi cảm ứng", "chết nguồn", "bị lỗi"]

    has_likenew = any(kw in bl for kw in kw_likenew)
    has_zin     = any(kw in bl or kw in tl for kw in kw_zin)
    has_98      = any(kw in bl for kw in kw_98)
    has_scratch = any(kw in bl for kw in kw_scratch)
    has_danger  = any(kw in bl for kw in kw_danger)

    pin = pin_pct if pin_pct is not None else 80  # giả định trung bình nếu không có
    floor = _price_floor(dong_may)
    is_too_cheap = (floor > 0) and (gia > 0) and (gia < floor * 0.55)

    # ── Phân loại ────────────────────────────────────────────────
    # D: Hàng dựng / Lỗi
    if (is_too_cheap and has_danger) or (has_danger and has_scratch):
        return "D – Hàng dựng/Lỗi"

    # A: Hoàn hảo
    if has_likenew and has_zin and pin >= 90:
        return "A – Hoàn hảo"

    # B: Khá
    if (has_98 or has_zin) and not has_scratch:
        return "B – Khá"
    if has_likenew and (pin < 85):
        return "B – Khá"

    # C: Trung bình
    return "C – Trung bình"


def extract_ngoai_hinh(body: str) -> str:
    """Trích xuất mô tả ngắn về ngoại hình từ body."""
    bl = (body or "").lower()
    if any(kw in bl for kw in ["99%", "like new", "likenew", "như mới"]):
        return "Like New (99%)"
    if "98%" in bl:
        return "Đẹp (98%)"
    if "97%" in bl or "96%" in bl:
        return "Khá đẹp (96-97%)"
    if any(kw in bl for kw in ["trầy nhẹ", "xước nhẹ"]):
        return "Trầy nhẹ"
    if any(kw in bl for kw in ["trầy", "xước", "móp"]):
        return "Có trầy xước"
    return "Không rõ"


def extract_do_zin(body: str, tinh_trang: str) -> str:
    """Xác định mức độ Zin của máy."""
    bl = (body or "").lower()
    tl = (tinh_trang or "").lower()
    combined = bl + " " + tl
    if any(kw in combined for kw in ["full zin", "nguyên zin", "zin 100%"]):
        return "Full Zin"
    if any(kw in combined for kw in ["zin", "chưa sửa"]):
        return "Zin"
    if any(kw in combined for kw in ["thay màn", "thay pin", "thay vỏ", "sửa chữa", "thay linh kiện"]):
        return "Đã thay linh kiện"
    return "Không rõ"


def is_iphone(ad: dict) -> bool:
    """Kiểm tra tin đăng có phải iPhone từ 8 trở lên không."""
    # Lọc theo brand = 1 (Apple) và category = 5010 (Điện thoại)
    if ad.get("mobile_brand") != 1:
        return False
    if ad.get("category") != 5010:
        return False
    # Kiểm tra tên model (trong params hoặc subject)
    model_val = get_param_value(ad.get("params", []), "mobile_model").lower()
    subject   = ad.get("subject", "").lower()
    # Áp dụng whitelist model
    text_to_check = model_val + " " + subject
    return any(m in text_to_check for m in IPHONE_MODELS_INCLUDE)


def extract_record(ad: dict) -> dict:
    """Chuyển một ad JSON → dict với đầy đủ các trường + Pin + Đánh giá."""
    params = ad.get("params", [])
    body   = ad.get("body", "")  # mô tả chi tiết

    # ── Địa chỉ ──────────────────────────────
    phuong    = ad.get("ward_name_v3", ad.get("ward_name", ""))
    quan      = ad.get("area_name", "")
    thanh_pho = ad.get("region_name_v3", ad.get("region_name", ""))

    # ── Loại người bán ───────────────────────
    if ad.get("company_ad") is True:
        loai_nguoi_ban = "Bán chuyên"
    elif ad.get("type") == "s":
        loai_nguoi_ban = "Cá nhân"
    else:
        loai_nguoi_ban = "Bán chuyên"

    # ── Tình trạng ───────────────────────────
    tinh_trang = get_param_value(params, "elt_condition")
    if not tinh_trang:
        tinh_trang = map_condition(ad.get("elt_condition", 0))

    # ── Hãng & Dòng máy ──────────────────────
    dong_may = get_param_value(params, "mobile_model")
    if dong_may:
        hang_dong_may = f"Apple / {dong_may}"
    else:
        hang_dong_may = "Apple / iPhone"

    # ── Phiên bản (lock) ─────────────────────
    phien_ban = get_param_value(params, "elt_lock")
    if not phien_ban:
        lock_code = ad.get("elt_lock", 0)
        phien_ban = map_lock(lock_code) if lock_code else "Quốc tế (Không khoá mạng)"

    # ── Xuất xứ ──────────────────────────────
    xuat_xu = get_param_value(params, "elt_origin")
    if not xuat_xu:
        xuat_xu = map_origin(ad.get("elt_origin", 0)) if ad.get("elt_origin") else "Không rõ"

    # ── Màu sắc ──────────────────────────────
    mau_sac = get_param_value(params, "mobile_color")
    if not mau_sac:
        mau_sac = map_color(ad.get("mobile_color", 0)) if ad.get("mobile_color") else "Không rõ"

    # ── Dung lượng ───────────────────────────
    dung_luong = get_param_value(params, "mobile_capacity")

    # ── Bảo hành ─────────────────────────────
    bao_hanh = get_param_value(params, "elt_warranty")
    if not bao_hanh:
        bao_hanh = "Không rõ"

    # ── Giá tiền ─────────────────────────────
    gia = ad.get("price", 0)

    # ── [MỚI] Tình trạng pin (%) ─────────────
    pin_pct = extract_pin(params, body)

    # ── [MỚI] Ngoại hình & Độ Zin ───────────
    ngoai_hinh = extract_ngoai_hinh(body)
    do_zin     = extract_do_zin(body, tinh_trang)

    # ── [MỚI] Đánh giá chất lượng ───────────
    danh_gia = danh_gia_chat_luong(
        body=body,
        pin_pct=pin_pct,
        gia=int(gia) if gia else 0,
        tinh_trang=tinh_trang,
        dong_may=dong_may or "",
    )

    return {
        "Tiêu đề"              : ad.get("subject", ""),
        "Phường"               : phuong,
        "Quận / Huyện"         : quan,
        "Thành phố"            : thanh_pho,
        "Loại người bán"       : loai_nguoi_ban,
        "Tình trạng"           : tinh_trang,
        "Hãng & Dòng máy"      : hang_dong_may,
        "Phiên bản"            : phien_ban,
        "Xuất xứ"              : xuat_xu,
        "Màu sắc"              : mau_sac,
        "Dung lượng"           : dung_luong,
        "Chính sách bảo hành"  : bao_hanh,
        "Giá (VNĐ)"            : gia,
        "Giá (hiển thị)"       : ad.get("price_string", ""),
        "Tình_Trạng_Pin (%)"   : pin_pct,           # số nguyên hoặc None
        "Ngoại hình"           : ngoai_hinh,
        "Độ Zin"               : do_zin,
        "Đánh_Giá_Chất_Lượng" : danh_gia,
        "Ngày đăng"            : ad.get("date", ""),
        "ID tin"               : ad.get("list_id", ""),
        "Link"                 : f"https://xe.chotot.com/mua-ban-dien-thoai/{ad.get('list_id', '')}",
        "Scraped at"           : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ──────────────────────────────────────────────
#  HÀM LẤY DỮ LIỆU TỪ API
# ──────────────────────────────────────────────

def fetch_page(offset: int, session: requests.Session) -> list:
    """Gọi API một trang, trả về danh sách ads Apple iPhone."""
    url = "https://gateway.chotot.com/v1/public/ad-listing"
    params = {
        "cg"                : 5010,   # Danh mục: Điện thoại
        "mobile_brand"      : 1,      # Apple
        "o"                 : offset,
        "limit"             : PAGE_SIZE,
        "key_param_included": "true",
        # Không dùng st=u,h vì sẽ trả về rỗng
    }
    headers = {
        "User-Agent"     : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept"         : "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Referer"        : "https://www.chotot.com/",
    }
    try:
        r = session.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("ads", [])
    except Exception as e:
        log.error(f"Lỗi khi lấy trang offset={offset}: {e}")
        return []


def scrape_all_pages(max_pages: int = MAX_PAGES) -> list[dict]:
    """Cào MAX_PAGES trang Apple từ API, lọc iPhone 8+, trả về list records."""
    all_records = []
    session = requests.Session()

    log.info(f"Bắt đầu cào dữ liệu – {max_pages} trang × {PAGE_SIZE} tin/trang")

    for page in range(max_pages):
        offset = page * PAGE_SIZE
        log.info(f"  Đang lấy trang {page + 1}/{max_pages}  (offset={offset})…")

        ads = fetch_page(offset, session)
        if not ads:
            log.warning("  Không có dữ liệu, dừng sớm.")
            break

        iphone_count = 0
        for ad in ads:
            # API đã lọc Apple (mobile_brand=1), ta chỉ kiểm tra whitelist model
            if is_iphone(ad):
                record = extract_record(ad)
                all_records.append(record)
                iphone_count += 1

        log.info(f"  → {len(ads)} tin Apple, {iphone_count} iPhone phù hợp | Tổng: {len(all_records)}")
        time.sleep(SLEEP_SEC)

    log.info(f"Hoàn tất cào. Tổng số bản ghi iPhone: {len(all_records)}")
    return all_records


# ──────────────────────────────────────────────
#  XUẤT EXCEL (APPEND-ONLY MỖI NGÀY)
# ──────────────────────────────────────────────

def save_to_excel(records: list[dict]) -> Path:
    """Lưu dữ liệu vào file Excel theo ngày, append nếu file đã tồn tại."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    excel_path = OUTPUT_DIR / f"chotot_iphone_{today}.xlsx"

    df_new = pd.DataFrame(records)

    if excel_path.exists():
        df_old = pd.read_excel(excel_path)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined.drop_duplicates(subset=["ID tin"], keep="last", inplace=True)
    else:
        df_combined = df_new

    # Định dạng cột giá
    df_combined["Giá (VNĐ)"] = pd.to_numeric(df_combined["Giá (VNĐ)"], errors="coerce")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_combined.to_excel(writer, sheet_name="iPhone_Listings", index=False)

        # Auto-fit cột
        ws = writer.sheets["iPhone_Listings"]
        for col in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value else 0) for cell in col
            )
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 50)

    log.info(f"Da luu file: {excel_path}  ({len(df_combined)} dong)")
    return excel_path


def save_to_csv(records: list[dict]) -> Path:
    """Cũng lưu thêm CSV (dễ đọc bằng nhiều công cụ)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = OUTPUT_DIR / f"chotot_iphone_{today}.csv"

    df = pd.DataFrame(records)
    write_header = not csv_path.exists()
    df.to_csv(csv_path, mode="a", index=False, header=write_header, encoding="utf-8-sig")
    log.info(f"Da luu CSV: {csv_path}")
    return csv_path


# ──────────────────────────────────────────────
#  XUẤT GOOGLE SHEETS (REAL-TIME)
# ──────────────────────────────────────────────

def _col_letter(n: int) -> str:
    """Chuyển số cột (1-indexed) thành chữ cái cột (A, B, …, Z, AA, …)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def upload_to_gsheet(records: list[dict]) -> str | None:
    """
    Upload records lên Google Sheet – MỖI NGÀY MỘT TAB RIÊNG.

    Quy tắc:
    - Tab được đặt tên theo ngày hôm nay, ví dụ: '2026-04-13'
    - Nếu tab chưa tồn tại → tạo mới
    - Nếu tab đã tồn tại   → merge + dedup theo 'ID tin' rồi ghi lại
    - Trả về URL Google Sheet hoặc None nếu lỗi
    """
    if not GSHEET_ENABLED:
        if not GSPREAD_AVAILABLE:
            log.warning("[GSheet] Thu vien gspread chua cai. Chay: pip install gspread google-auth")
        elif not GSHEET_CREDENTIALS.exists():
            log.warning(f"[GSheet] Khong tim thay file credentials: {GSHEET_CREDENTIALS}")
            log.warning("[GSheet] Xem huong dan trong SETUP_GOOGLE_SHEET.md")
        elif not GSHEET_SPREADSHEET_ID:
            log.warning("[GSheet] Chua dien GSHEET_SPREADSHEET_ID trong script!")
        return None

    try:
        # ── Xác thực ────────────────────────────────────────────
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_file(str(GSHEET_CREDENTIALS), scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(GSHEET_SPREADSHEET_ID)
        sheet_url   = f"https://docs.google.com/spreadsheets/d/{GSHEET_SPREADSHEET_ID}"

        # ── Tìm hoặc tạo tab theo ngày hôm nay ─────────────────
        today_tab = datetime.now().strftime("%Y-%m-%d")
        existing_titles = [ws.title for ws in spreadsheet.worksheets()]

        if today_tab in existing_titles:
            ws = spreadsheet.worksheet(today_tab)
            log.info(f"[GSheet] Tab '{today_tab}' da ton tai – se merge du lieu...")
            # Lấy dữ liệu cũ trong tab để merge
            existing_data = ws.get_all_records()
            df_old = pd.DataFrame(existing_data) if existing_data else pd.DataFrame()
        else:
            ws = spreadsheet.add_worksheet(title=today_tab, rows=2000, cols=30)
            log.info(f"[GSheet] Da tao tab moi: '{today_tab}'")
            df_old = pd.DataFrame()

        # ── Merge + dedup ───────────────────────────────────────
        df_new = pd.DataFrame(records)
        if not df_old.empty and "ID tin" in df_old.columns:
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            df_all.drop_duplicates(subset=["ID tin"], keep="last", inplace=True)
            df_all.sort_values("ID tin", ascending=False, inplace=True)
            df_all.reset_index(drop=True, inplace=True)
        else:
            df_all = df_new.copy()

        # ── Chuẩn bị data ───────────────────────────────────────
        df_all = df_all.fillna("")
        # Giữ pin là số, chuyển các cột còn lại sang str để tránh lỗi type
        for col in df_all.columns:
            if col not in ("Tình_Trạng_Pin (%)", "Giá (VNĐ)"):
                df_all[col] = df_all[col].astype(str)
        df_all["Giá (VNĐ)"] = pd.to_numeric(df_all["Giá (VNĐ)"], errors="coerce").fillna(0).astype(int)

        headers = list(df_all.columns)
        rows    = df_all.values.tolist()
        n_cols  = len(headers)
        n_rows  = len(rows)

        # ── Ghi lên sheet ───────────────────────────────────────
        ws.clear()
        ws.update([headers] + rows, value_input_option="USER_ENTERED")

        # ── Định dạng header ────────────────────────────────────
        last_col = _col_letter(n_cols)
        ws.format(f"A1:{last_col}1", {
            "textFormat"         : {"bold": True, "fontSize": 10, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor"    : {"red": 0.13, "green": 0.13, "blue": 0.13},
            "horizontalAlignment": "CENTER",
        })

        # ── Định dạng cột Giá (VNĐ) ────────────────────────────
        try:
            price_idx    = headers.index("Giá (VNĐ)") + 1
            price_letter = _col_letter(price_idx)
            ws.format(f"{price_letter}2:{price_letter}{n_rows + 1}", {
                "horizontalAlignment": "RIGHT",
                "numberFormat"       : {"type": "NUMBER", "pattern": "#,##0"},
            })
        except (ValueError, KeyError):
            pass

        # ── Định dạng cột Tình_Trạng_Pin ───────────────────────
        try:
            pin_idx    = headers.index("Tình_Trạng_Pin (%)") + 1
            pin_letter = _col_letter(pin_idx)
            ws.format(f"{pin_letter}2:{pin_letter}{n_rows + 1}", {
                "horizontalAlignment": "CENTER",
            })
        except (ValueError, KeyError):
            pass

        # ── Định dạng cột Đánh_Giá_Chất_Lượng (màu theo loại) ─
        try:
            dg_idx    = headers.index("Đánh_Giá_Chất_Lượng") + 1
            dg_letter = _col_letter(dg_idx)
            COLOR_MAP_DG = {
                "A": {"red": 0.20, "green": 0.78, "blue": 0.35},   # xanh lá
                "B": {"red": 0.27, "green": 0.51, "blue": 0.95},   # xanh dương
                "C": {"red": 1.0,  "green": 0.76, "blue": 0.03},   # vàng
                "D": {"red": 0.90, "green": 0.22, "blue": 0.21},   # đỏ
            }
            for i, row in enumerate(rows, start=2):
                cell_val = str(row[dg_idx - 1])
                grade    = cell_val[0] if cell_val else ""
                if grade in COLOR_MAP_DG:
                    ws.format(f"{dg_letter}{i}", {
                        "backgroundColor"    : COLOR_MAP_DG[grade],
                        "horizontalAlignment": "CENTER",
                        "textFormat"         : {"bold": True},
                    })
        except (ValueError, KeyError):
            pass

        log.info(f"[GSheet] Da upload {len(df_all)} dong vao tab '{today_tab}'!")
        log.info(f"[GSheet] URL: {sheet_url}")
        return sheet_url

    except gspread.exceptions.APIError as e:
        log.error(f"[GSheet] Loi Google Sheets API: {e}")
    except FileNotFoundError:
        log.error(f"[GSheet] Khong tim thay file credentials: {GSHEET_CREDENTIALS}")
    except Exception as e:
        log.error(f"[GSheet] Loi khong xac dinh: {e}")
    return None


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    log.info("=" * 55)
    log.info(" CHOTOT IPHONE SCRAPER – bat dau")
    log.info(f"  Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    records = scrape_all_pages(max_pages=MAX_PAGES)

    if not records:
        log.warning("Khong tim thay tin iPhone nao! Kiem tra lai bo loc.")
        return

    excel_path  = save_to_excel(records)
    csv_path    = save_to_csv(records)
    sheet_url   = upload_to_gsheet(records)   # <-- Google Sheets

    # In preview (dùng sys.stdout để tránh lỗi cp1252 trên Windows)
    import sys, io
    df = pd.DataFrame(records)
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") \
          if hasattr(sys.stdout, "buffer") else sys.stdout
    sep = "=" * 75
    out.write(f"\n{sep}\n")
    out.write("  [DU LIEU MAU - 10 DONG DAU]:\n")
    out.write(f"{sep}\n")
    preview_cols = [
        "Hãng & Dòng máy",
        "Dung lượng",
        "Giá (VNĐ)",
        "Tình_Trạng_Pin (%)",
        "Ngoại hình",
        "Độ Zin",
        "Đánh_Giá_Chất_Lượng",
    ]
    # Chỉ lấy cột tồn tại trong df
    avail = [c for c in preview_cols if c in df.columns]
    out.write(df[avail].head(10).to_string(index=True) + "\n")
    out.write(f"{sep}\n")
    # Thống kê nhanh đánh giá
    if "Đánh_Giá_Chất_Lượng" in df.columns:
        out.write("\n  [THONG KE DANH GIA CHAT LUONG]:\n")
        stats = df["Đánh_Giá_Chất_Lượng"].value_counts().to_string()
        out.write(stats + "\n")
    out.write(f"\n  [Excel]        : {excel_path}\n")
    out.write(f"  [CSV  ]        : {csv_path}\n")
    if sheet_url:
        out.write(f"  [Google Sheet] : {sheet_url}\n")
    else:
        out.write(f"  [Google Sheet] : Chua cau hinh (xem SETUP_GOOGLE_SHEET.md)\n")
    out.write(f"  [Tong tin]     : {len(records)} tin iPhone\n\n")
    out.flush()

    log.info("=" * 55)
    log.info("  HOAN TAT")
    log.info("=" * 55)


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════
#  HƯỚNG DẪN TỰ ĐỘNG HÓA (WINDOWS TASK SCHEDULER)
# ══════════════════════════════════════════════════════════════
#  Bước 1: Mở Task Scheduler → "Create Basic Task"
#  Bước 2: Đặt tên: "Chotot iPhone Scraper"
#  Bước 3: Trigger: "Daily" → chọn giờ chạy (ví dụ: 08:00)
#  Bước 4: Action: "Start a program"
#     Program/script:  C:\Python312\python.exe  (đường dẫn Python của bạn)
#     Add arguments :  scrape_chotot_iphone.py
#     Start in      :  C:\Users\ADMIN\Downloads\cao_du_lieu_ien_thoai_iphon\
#  Bước 5: Finish → Done!
#  Hoặc dùng lệnh PowerShell (chạy với quyền Admin):
#  $action  = New-ScheduledTaskAction `
#               -Execute 'python.exe' `
#               -Argument 'scrape_chotot_iphone.py' `
#               -WorkingDirectory 'C:\Users\ADMIN\Downloads\cao_du_lieu_ien_thoai_iphon'
#  $trigger = New-ScheduledTaskTrigger -Daily -At 08:00AM
#  Register-ScheduledTask -Action $action -Trigger $trigger `
#               -TaskName "ChhototIPhoneScraper" -RunLevel Highest
