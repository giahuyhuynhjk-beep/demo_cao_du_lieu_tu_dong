# ==============================================================
#  iPhone Data Cleaning Script
#  Tương thích: pandas 1.x và 2.x, Python 3.8+
#  Chạy: python iphone_cleaning.py
#  Hoặc copy từng cell vào Jupyter Notebook
# ==============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import re, glob, os
from scipy import stats

matplotlib.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.float_format', '{:,.0f}'.format)
print(' Libraries loaded')

# ── CELL 1: Load dữ liệu ──────────────────────────────────────
OUTPUT_DIR = 'output'
csv_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'chotot_iphone_*.csv')))
if not csv_files:
    raise FileNotFoundError(f'Không tìm thấy CSV trong "{OUTPUT_DIR}/"')

latest_file = csv_files[-1]
print(f' Tải file: {latest_file}')

df_raw = pd.read_csv(latest_file, encoding='utf-8-sig')
print(f'\nKích thước gốc: {df_raw.shape[0]:,} hàng × {df_raw.shape[1]} cột')
print('\nCác cột:')
for c in df_raw.columns:
    print(f'   • {c}')

# ── CELL 2: Helper functions ───────────────────────────────────

def extract_model(hang_dong):
    """Apple / iPhone 14 Pro Max  →  iPhone 14 Pro Max"""
    if not isinstance(hang_dong, str):
        return 'Unknown'
    parts = hang_dong.split('/')
    return parts[-1].strip() if len(parts) > 1 else hang_dong.strip()


def extract_dungluong(s):
    """'128 GB' → 128.0 | '1 TB' → 1024.0"""
    if not isinstance(s, str):
        return np.nan
    m = re.search(r'([\d]+(?:\.\d+)?)', s.lower())
    if not m:
        return np.nan
    val = float(m.group(1))
    return val * 1024 if 'tb' in s.lower() else val


def encode_dozin(val):
    """'Zin' → 1  |  mọi thứ khác → 0"""
    if not isinstance(val, str):
        return 0
    return 1 if val.strip().lower() in ('zin', 'nguyên zin', 'nguyen zin', 'full zin') else 0


def encode_ngoaihinh(val):
    """'Like New (99%)' → 99 | 'Không rõ' → NaN"""
    if pd.isna(val):
        return np.nan
    m = re.search(r'(\d{2,3}(?:\.\d)?)\s*%', str(val))
    if m:
        v = float(m.group(1))
        return v if 50 <= v <= 100 else np.nan
    return np.nan


def encode_phienban(val):
    """Quốc tế → 1  |  Lock → 0"""
    if not isinstance(val, str):
        return 0
    v = val.lower()
    return 1 if ('không khoá' in v or 'quốc tế' in v or 'unlocked' in v) else 0


# Fallback regex cho schema cũ
def regex_pin(title):
    if not isinstance(title, str):
        return np.nan
    t = title.lower()
    for pat in [
        r'pin\s*[:=\s]*([89]\d|100)',
        r'p\s*[:=]?\s*([89]\d|100)\s*%',
        r'pin\s*([89]\d|100)\s*%?',
        r'([89]\d|100)\s*%\s*(?:pin|battery)',
        r'\bp([89]\d|100)\b',
    ]:
        m = re.search(pat, t)
        if m:
            v = int(m.group(1))
            if 70 <= v <= 100:
                return float(v)
    return np.nan


def regex_ngoaihinh(title):
    if not isinstance(title, str):
        return np.nan
    t = title.lower()
    for pat in [
        r'(?:đẹp|máy|ngoại\s*hình|còn)?\s*([89]\d(?:\.\d)?|100)\s*%',
        r'(\d{2,3}(?:\.\d)?)\s*%\s*(?:đẹp|mới|zin|nguyên)',
    ]:
        m = re.search(pat, t)
        if m:
            v = float(m.group(1))
            if 80 <= v <= 100:
                ctx = t[max(0, m.start()-10):m.start()]
                if 'pin' in ctx or ' p' in ctx:
                    continue
                return v
    return np.nan


def regex_dozin(title, condition):
    title = str(title).lower() if isinstance(title, str) else ''
    condition = str(condition).lower() if isinstance(condition, str) else ''
    if 'sửa chữa' in condition or 'thay linh kiện' in condition:
        return 0
    for kw in ['thay màn', 'thay linh kiện', 'thay pin', 'mất face',
               'mất sóng', 'lưng nứt', 'fix', 'linh kiện', 'cấn', 'vỡ']:
        if kw in title:
            return 0
    for kw in ['nguyên zin', 'full zin', 'zin chuẩn', 'bao zin', 'zin áp', ' zin ']:
        if kw in title:
            return 1
    return 1 if 'chưa sửa chữa' in condition else 0


# ── CELL 3: Detect schema & chuẩn hoá ─────────────────────────
COLS = df_raw.columns.tolist()
HAS_PIN  = 'Tình_Trạng_Pin (%)' in COLS
HAS_NH   = 'Ngoại hình' in COLS
HAS_DZIN = 'Độ Zin' in COLS
NEW_SCHEMA = HAS_PIN and HAS_NH and HAS_DZIN

print(f'\nSchema: {"MỚI" if NEW_SCHEMA else "CŨ (regex)"}')

df = df_raw.copy()
df['Model']         = df['Hãng & Dòng máy'].apply(extract_model)
df['Dung_luong_GB'] = df['Dung lượng'].apply(extract_dungluong)
df['Phien_ban']     = df['Phiên bản'].apply(encode_phienban)
df['Xuat_xu']       = df['Xuất xứ'].copy()

if NEW_SCHEMA:
    df['Tinh_Trang_Pin'] = pd.to_numeric(df['Tình_Trạng_Pin (%)'], errors='coerce')
    df['Ngoai_hinh']     = df['Ngoại hình'].apply(encode_ngoaihinh)
    df['Do_Zin']         = df['Độ Zin'].apply(encode_dozin)
else:
    df['Tinh_Trang_Pin'] = df['Tiêu đề'].apply(regex_pin)
    df['Ngoai_hinh']     = df['Tiêu đề'].apply(regex_ngoaihinh)
    df['Do_Zin']         = df.apply(
        lambda r: regex_dozin(r['Tiêu đề'], r['Tình trạng']), axis=1)

print(f'   Pin: {df["Tinh_Trang_Pin"].notna().sum()} / {len(df)}')
print(f'   NH : {df["Ngoai_hinh"].notna().sum()} / {len(df)}')
print(f'   Zin: {df["Do_Zin"].value_counts().to_dict()}')
print(f'   PB : {df["Phien_ban"].value_counts().to_dict()}')

# ── CELL 4: Data Selection ────────────────────────────────────
SELECTED = {
    'Model':          'Model',
    'Dung_luong_GB':  'Dung_luong',
    'Giá (VNĐ)':      'Gia_VND',
    'Tinh_Trang_Pin': 'Tinh_Trang_Pin',
    'Ngoai_hinh':     'Ngoai_hinh',
    'Do_Zin':         'Do_Zin',
    'Phien_ban':      'Phien_ban',
    'Xuat_xu':        'Xuat_xu',
}

df_clean = df[list(SELECTED.keys())].rename(columns=SELECTED).copy()
df_clean['Gia_VND'] = pd.to_numeric(df_clean['Gia_VND'], errors='coerce')
print(f'\n📦 Shape: {df_clean.shape}')

# ══════════════════════════════════════════════════════════════
#  CELL 5 — Level 2: Predictive Imputation for Battery Health
#  Cách AI "đoán" % Pin:
#    - Mã hoá Model → số nguyên (LabelEncoder)
#    - Dùng [Gia_VND, Model_ID, Ngoai_hinh, Do_Zin, Dung_luong]
#      làm features để huấn luyện Random Forest
#    - IterativeImputer lặp 10 vòng để giá trị hội tụ chính xác
#    - Kết quả được clip về [70, 100] để hợp lý với thực tế
# ══════════════════════════════════════════════════════════════

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor

# Bật IterativeImputer (còn là experimental trong sklearn)
from sklearn.experimental import enable_iterative_imputer   # noqa: F401
from sklearn.impute import IterativeImputer

print('--- Level 2: Predictive Imputation for Battery Health ---')
pin_missing_before = df_clean['Tinh_Trang_Pin'].isna().sum()
print(f'Pin bi thieu truoc: {pin_missing_before} / {len(df_clean)} hang')

# ── Bước 1: Mã hoá Model → Model_ID ────────────────────────────
le = LabelEncoder()
df_clean['Model_ID'] = le.fit_transform(df_clean['Model'].astype(str))

# ── Bước 2: Đảm bảo các cột số đúng kiểu ───────────────────────
for col in ['Gia_VND', 'Ngoai_hinh', 'Do_Zin', 'Dung_luong']:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

# ── Bước 3: Điền tạm Ngoai_hinh bằng median để RF có đủ features
nh_temp_median = df_clean['Ngoai_hinh'].median()
df_clean['Ngoai_hinh_temp'] = df_clean['Ngoai_hinh'].fillna(nh_temp_median)

# ── Bước 4: Chuẩn bị ma trận đầu vào cho IterativeImputer ──────
#  Features: [Gia_VND, Model_ID, Ngoai_hinh_temp, Do_Zin, Dung_luong]
#  Target bị thiếu: Tinh_Trang_Pin (cột cuối)
IMPUTE_COLS = ['Gia_VND', 'Model_ID', 'Ngoai_hinh_temp',
               'Do_Zin', 'Dung_luong', 'Tinh_Trang_Pin']

X_impute = df_clean[IMPUTE_COLS].copy()

# ── Bước 5: Khởi tạo IterativeImputer với RandomForest estimator
rf_estimator = RandomForestRegressor(
    n_estimators=100,    # 100 cây quyết định
    max_depth=8,         # Giới hạn độ sâu tránh overfitting
    random_state=42,
    n_jobs=-1            # Dùng tất cả CPU core
)

imputer = IterativeImputer(
    estimator=rf_estimator,
    max_iter=10,         # 10 vòng lặp để hội tụ
    random_state=42,
    verbose=1            # In tiến trình từng vòng lặp
)

# ── Bước 6: Chạy predictive imputation ─────────────────────────
print('\nDang huan luyen RandomForest de du doan % Pin...')
X_imputed = imputer.fit_transform(X_impute)
X_imputed_df = pd.DataFrame(X_imputed, columns=IMPUTE_COLS)

# ── Bước 7: Lấy cột Pin đã dự đoán & clip về [70, 100] ─────────
df_clean['Tinh_Trang_Pin'] = (
    X_imputed_df['Tinh_Trang_Pin']
    .clip(lower=70, upper=100)    # Pin thực tế không nằm ngoài 70-100%
    .round(1)
)

# Dọn dẹp cột tạm
df_clean.drop(columns=['Ngoai_hinh_temp'], inplace=True)

# ── Bước 8: Kiểm tra kết quả ────────────────────────────────────
pin_missing_after = df_clean['Tinh_Trang_Pin'].isna().sum()
print(f'\n[KIEM TRA] df.isnull().sum() cho Tinh_Trang_Pin = {pin_missing_after}')
assert pin_missing_after == 0, "Con gia tri PIN bi thieu!"
print('>>> Tat ca gia tri Pin da duoc dien day du!')

# ── Bước 9: Bảng so sánh 10 dòng đầu ───────────────────────────
print('\n--- Bang kiem tra 10 dong dau (Model / Gia / Pin) ---')
check_cols = ['Model', 'Gia_VND', 'Tinh_Trang_Pin']
print(df_clean[check_cols].head(10).to_string(index=True))

print(f'\nThong ke Tinh_Trang_Pin sau imputation:')
print(df_clean['Tinh_Trang_Pin'].describe().to_string())

# ── CELL 6: Xóa hàng thiếu bắt buộc ──────────────────────────
n0 = len(df_clean)
df_clean = df_clean.dropna(subset=['Gia_VND', 'Dung_luong'])
df_clean = df_clean[df_clean['Gia_VND'] > 0]

global_nh = df_clean['Ngoai_hinh'].median()
df_clean['Ngoai_hinh'] = df_clean['Ngoai_hinh'].fillna(global_nh)
df_clean = df_clean.reset_index(drop=True)
print(f'Loại {n0 - len(df_clean)} hàng | còn: {len(df_clean):,}')

# ── CELL 7: Outlier Removal — IQR + Z-score ───────────────────
# Dùng for-loop để tương thích pandas 1.x và 2.x (tránh lỗi KeyError 'Model')
def iqr_filter(group, col='Gia_VND', lo=1.5, hi=3.0):
    if len(group) < 5:
        return group
    Q1, Q3 = group[col].quantile(0.25), group[col].quantile(0.75)
    IQR = Q3 - Q1
    if IQR == 0:
        return group
    return group[(group[col] >= Q1 - lo * IQR) & (group[col] <= Q3 + hi * IQR)]


n_before = len(df_clean)

# --- For-loop thay vì groupby().apply() ---
frames = []
for model_name, group in df_clean.groupby('Model'):
    frames.append(iqr_filter(group))
df_clean = pd.concat(frames, ignore_index=True)

# Z-score toàn cục |z| > 4
z = np.abs(stats.zscore(df_clean['Gia_VND'].values))
df_clean = df_clean[z < 4].reset_index(drop=True)

removed = n_before - len(df_clean)
print(f'Outlier: loại {removed} ({removed/n_before*100:.1f}%) | còn {len(df_clean):,}')
print(df_clean['Gia_VND'].describe().rename('Gia_VND (VNĐ)').to_string())

# ── CELL 8: Preview ───────────────────────────────────────────
print(f'\nDữ liệu sạch: {df_clean.shape}')
print(df_clean.head(5).to_string())

# ── CELL 9: Histogram giá ─────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('Phân phối giá trước và sau khi lọc Outlier', fontsize=14, fontweight='bold')

axes[0].hist(df_raw['Giá (VNĐ)'].dropna() / 1e6, bins=60,
             color='#E74C3C', edgecolor='white', alpha=0.85)
axes[0].set_title('Trước'); axes[0].set_xlabel('Giá (triệu VNĐ)')
axes[0].grid(axis='y', alpha=0.3)

axes[1].hist(df_clean['Gia_VND'] / 1e6, bins=60,
             color='#2ECC71', edgecolor='white', alpha=0.85)
axes[1].set_title('Sau'); axes[1].set_xlabel('Giá (triệu VNĐ)')
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
os.makedirs(OUTPUT_DIR, exist_ok=True)
plt.savefig(f'{OUTPUT_DIR}/price_distribution.png', dpi=150, bbox_inches='tight')
plt.show()
print('Lưu: price_distribution.png')

# ── CELL 10: Correlation Heatmap ──────────────────────────────
NUMERIC_COLS = ['Gia_VND', 'Dung_luong', 'Tinh_Trang_Pin',
                'Ngoai_hinh', 'Do_Zin', 'Phien_ban']
LABELS = {
    'Gia_VND':         'Giá (VNĐ)',
    'Dung_luong':      'Dung lượng (GB)',
    'Tinh_Trang_Pin':  'Pin (%)',
    'Ngoai_hinh':      'Ngoại hình (%)',
    'Do_Zin':          'Độ Zin',
    'Phien_ban':       'Phiên bản',
}

df_corr = df_clean[NUMERIC_COLS].rename(columns=LABELS)

# Loại cột không có variance (tránh NaN trong correlation)
valid_cols = [c for c in df_corr.columns if df_corr[c].nunique() > 1]
dropped = set(df_corr.columns) - set(valid_cols)
if dropped:
    print(f' Bỏ cột không có variance: {dropped}')
df_corr = df_corr[valid_cols]

corr_matrix = df_corr.corr()

fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(corr_matrix, annot=True, fmt='.2f',
            cmap='RdYlGn', center=0, vmin=-1, vmax=1,
            linewidths=0.5, linecolor='white', square=True, ax=ax,
            cbar_kws={'shrink': 0.8, 'label': 'Pearson r'},
            annot_kws={'size': 11, 'weight': 'bold'})
ax.set_title('\n Ma Trận Tương Quan — Ảnh Hưởng Tới Giá iPhone\n',
             fontsize=14, fontweight='bold', pad=15)
ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right', fontsize=10)
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/correlation_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print(' Lưu: correlation_heatmap.png')

# In tương quan với Giá — đã dropna() để tránh ValueError
GIA_LABEL = 'Giá (VNĐ)'
if GIA_LABEL in corr_matrix.columns:
    gia_corr = (
        corr_matrix[GIA_LABEL]
        .drop(GIA_LABEL)
        .dropna()                  # bỏ NaN trước khi dùng int()
        .sort_values(ascending=False)
    )
    print(f'\nTương quan với {GIA_LABEL}:')
    for feat, val in gia_corr.items():
        bar = '█' * int(abs(val) * 20)
        direction = '↑' if val > 0 else '↓'
        print(f'   {direction} {feat:<20} {val:+.3f}  {bar}')

# ── CELL 11: Boxplot theo Model ────────────────────────────────
top_models = df_clean['Model'].value_counts().head(15).index
df_top = df_clean[df_clean['Model'].isin(top_models)].copy()
df_top['Gia_Trieu'] = df_top['Gia_VND'] / 1e6

model_order = (
    df_top.groupby('Model')['Gia_Trieu'].median()
    .sort_values().index.tolist()
)

fig, ax = plt.subplots(figsize=(14, 7))
sns.boxplot(data=df_top, x='Gia_Trieu', y='Model', order=model_order,
            palette='viridis', width=0.6, fliersize=3, ax=ax)
ax.set_title('Phân phối giá theo Model iPhone (Top 15)', fontsize=13, fontweight='bold')
ax.set_xlabel('Giá (triệu VNĐ)', fontsize=11)
ax.set_ylabel('')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/price_by_model_boxplot.png', dpi=150, bbox_inches='tight')
plt.show()
print('Lưu: price_by_model_boxplot.png')

# ── CELL 12: Lưu file ─────────────────────────────────────────
CSV_OUT = f'{OUTPUT_DIR}/iphone_cleaned.csv'
XLSX_OUT = f'{OUTPUT_DIR}/iphone_cleaned.xlsx'

df_clean.to_csv(CSV_OUT, index=False, encoding='utf-8-sig')
print(f'\nCSV  : {CSV_OUT}')

try:
    df_clean.to_excel(XLSX_OUT, index=False)
    print(f' Excel: {XLSX_OUT}')
except Exception as e:
    print(f' Excel: {e}')

print(f'\n═══ XONG ═══')
print(f'  Gốc: {len(df_raw):,} | Sạch: {len(df_clean):,} | Tỷ lệ giữ: {len(df_clean)/len(df_raw)*100:.1f}%')
