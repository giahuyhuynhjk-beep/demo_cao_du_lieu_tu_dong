import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import time
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(
    page_title="AI Định giá iPhone | Premium",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PREMIUM CSS INJECTION ---
st.markdown("""
<style>
    /* Nhập font mang hơi hướng Apple */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Nền Gradient Động (Animated Mesh Gradient) */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(-45deg, #fdfbfb, #ebedee, #f5f7fa, #e4efe9);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Glassmorphism cho Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.4);
    }

    /* Style cho các Card chứa Input */
    div[data-testid="stVerticalBlock"] > div:has(div.stSelectbox),
    div[data-testid="stVerticalBlock"] > div:has(div.stSlider) {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 1.2rem;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    div[data-testid="stVerticalBlock"] > div:has(div.stSelectbox):hover,
    div[data-testid="stVerticalBlock"] > div:has(div.stSlider):hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(0, 122, 255, 0.2);
    }

    /* Tùy chỉnh Header */
    h1 {
        font-family: 'SF Pro Display', sans-serif !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #1d1d1f 0%, #434344 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1.5px;
        text-align: center;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    h3 {
        font-weight: 700 !important;
        color: #1d1d1f;
        font-size: 1.2rem !important;
        margin-bottom: 1rem !important;
    }

    /* Nút bấm (Button) phong cách Premium */
    .stButton > button {
        background: linear-gradient(135deg, #007AFF 0%, #0056b3 100%);
        color: white;
        border-radius: 25px;
        padding: 0.8rem 2rem;
        font-size: 1.2rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 10px 20px rgba(0, 122, 255, 0.25);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        width: 100%;
        margin-top: 1rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 15px 30px rgba(0, 122, 255, 0.35);
        color: white;
        border: none;
    }
    
    .stButton > button:active {
        transform: translateY(1px);
    }
    
    /* Card Kết quả */
    .result-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(30px);
        -webkit-backdrop-filter: blur(30px);
        border-radius: 30px;
        padding: 3.5rem 2rem;
        box-shadow: 0 20px 50px rgba(0,0,0,0.08), inset 0 0 0 1px rgba(255,255,255,0.8);
        text-align: center;
        animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
        margin-top: 2rem;
    }
    
    /* Vạch màu Apple-like ở trên cùng Card */
    .result-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 6px;
        background: linear-gradient(90deg, #5AC8FA, #007AFF, #5856D6, #FF2D55);
    }

    .price-value {
        font-family: 'SF Pro Display', sans-serif;
        font-size: 4.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1d1d1f 0%, #434344 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0;
        letter-spacing: -2px;
        line-height: 1.1;
    }

    .badge-container {
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 2rem;
    }

    .premium-badge {
        background: rgba(0, 122, 255, 0.08);
        color: #007AFF;
        padding: 8px 18px;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 600;
        border: 1px solid rgba(0, 122, 255, 0.15);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .green-badge {
        background: rgba(52, 199, 89, 0.08);
        color: #34C759;
        border-color: rgba(52, 199, 89, 0.15);
    }

    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(40px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Ẩn Menu Streamlit và Header (Deploy button, v.v.) */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div.stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# --- CATEGORY MAPPINGS ---
GEN_MAP = {
    'iphone se':5,'iphone 7':7,'iphone 7 plus':7,
    'iphone 8':8,'iphone 8 plus':8,
    'iphone x':10,'iphone xs':10,'iphone xs max':10,'iphone xr':10,
    'iphone 11':11,'iphone 11 pro':11,'iphone 11 pro max':11,
    'iphone 12':12,'iphone 12 mini':12,'iphone 12 pro':12,'iphone 12 pro max':12,
    'iphone 13':13,'iphone 13 mini':13,'iphone 13 pro':13,'iphone 13 pro max':13,
    'iphone 14':14,'iphone 14 plus':14,'iphone 14 pro':14,'iphone 14 pro max':14,
    'iphone 15':15,'iphone 15 plus':15,'iphone 15 pro':15,'iphone 15 pro max':15,
    'iphone 16':16,'iphone 16 plus':16,'iphone 16 pro':16,
    'iphone 16 pro max':16,'iphone 16e':16,'iphone air':16,
    'iphone 17':17,'iphone 17 pro':17,'iphone 17 pro max':17,'iphone 17e':17,
}

# --- FEATURE ENGINEERING ---
def feature_engineering(df):
    df = df.copy()
    col_rename = {
        'Dòng máy':'Dong may', 'Phiên bản':'Phien ban',
        'Tình trạng':'Tinh trang', 'Xuất xứ':'Xuat xu',
        'Dung lượng (GB)':'Dung luong (GB)',
        'Pin_bucket':'Pin_bucket',
        'Chính sách bảo hành':'Chinh sach bao hanh',
        'Tinh_trang_tong_hop':'Tinh_trang_tong_hop'
    }
    df = df.rename(columns=col_rename)
    
    dl = df['Dong may'].str.lower().str.strip()
    df['Gen']         = dl.map(GEN_MAP).fillna(10).astype(int)
    df['Is_Pro']      = dl.str.contains('pro').astype(int)
    df['Is_ProMax']   = dl.str.contains('pro max').astype(int)
    df['Is_Plus']     = dl.str.contains('plus').astype(int)
    df['Is_Mini']     = dl.str.contains('mini').astype(int)
    df['Is_Air']      = dl.str.contains('air').astype(int)
    
    pin_map = {'Dưới 80%':0,'80-84%':1,'85-89%':2,'90-94%':3,'95-96%':4,'97-99%':5,'100%':6}
    df['Pin_score']   = df['Pin_bucket'].str.strip().map(pin_map).fillna(3).astype(int)
    
    bh_map  = {'Hết bảo hành':0,'Còn bảo hành':1,'3 tháng':1,'4-6 tháng':2,'7-12 tháng':3,'>12 tháng':4}
    df['BH_score']    = df['Chinh sach bao hanh'].str.strip().map(bh_map).fillna(0).astype(int)
    
    tt_map  = {'Đã sửa chữa / thay linh kiện':0,'Đã sử dụng (chưa sửa chữa)':1,'Mới':2}
    df['TT_score']    = df['Tinh trang'].str.strip().map(tt_map).fillna(1).astype(int)
    
    tth = df['Tinh_trang_tong_hop'].str.lower().fillna('')
    df['Is_Zin']        = tth.str.contains('zin').astype(int)
    df['Is_No_Scratch'] = tth.str.contains('không trầy').astype(int)
    df['Has_ManThay']   = tth.str.contains('màn thay|main thay').astype(int)
    df['Has_PinThay']   = tth.str.contains('pin thay').astype(int)
    
    df['Is_QuocTe']     = df['Phien ban'].str.contains('Quoc te', na=False).astype(int)
    df['Gen_sq']        = df['Gen'] ** 2
    df['Storage_x_Gen'] = df['Dung luong (GB)'] * df['Gen']
    
    features = ['Dong may', 'Xuat xu', 'Dung luong (GB)', 'Gen', 'Is_Pro', 'Is_ProMax', 
                'Is_Plus', 'Is_Mini', 'Is_Air', 'Pin_score', 'BH_score', 'TT_score', 
                'Is_Zin', 'Is_No_Scratch', 'Has_ManThay', 'Has_PinThay', 'Is_QuocTe', 
                'Gen_sq', 'Storage_x_Gen']
    return df[features]

# --- LOAD MODEL ---
BEST_MODEL_FILE = "xgboost_best_model.pkl"

@st.cache_resource
def load_best_model():
    path = os.path.join('output', BEST_MODEL_FILE)
    if not os.path.exists(path): return None
    with open(path, 'rb') as f:
        obj = pickle.load(f)
        return obj['pipeline'] if isinstance(obj, dict) and 'pipeline' in obj else obj

# --- SIDEBAR: DESIGNED FOR PREMIUM FEEL ---
# --- LOAD MODEL ---
current_model = load_best_model()

# --- MAIN APP ---
st.title("🍏 Định giá iPhone AI")

if current_model is None:
    st.error("❌ Không tìm thấy model trong thư mục `output/`.")
else:
    # Bố cục 3 cột cho cảm giác gọn gàng, hiện đại
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📱 Thông số thiết bị")
        dong_may = st.selectbox("Dòng máy", [
            "iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone 17", "iPhone 17e",
            "iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 16 Plus", "iPhone 16", "iPhone 16e",
            "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15",
            "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14",
            "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13 Mini", "iPhone 13",
            "iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12 Mini", "iPhone 12",
            "iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11",
            "iPhone XS Max", "iPhone XS", "iPhone XR", "iPhone X",
            "iPhone 8 Plus", "iPhone 8", "iPhone 7 Plus", "iPhone 7", "iPhone SE", "iPhone Air"
        ])
        dung_luong = st.selectbox("Dung lượng lưu trữ", [32, 64, 128, 256, 512, 1024], index=2)
        phien_ban = st.selectbox("Phiên bản", ["Quốc tế (Không khoá mạng)", "Khóa mạng (Lock)"])

    with col2:
        st.markdown("### 🛠️ Tình trạng máy")
        tinh_trang = st.selectbox("Phân loại tình trạng", [
            "Đã sử dụng (chưa sửa chữa)", "Đã sửa chữa / thay linh kiện", "Mới"
        ])
        tinh_trang_chi_tiet = st.selectbox("Độ Zin & Chi tiết", [
            "Zin không trầy xước", "Zin trầy xước", "Pin thay", "Màn thay", 
            "Main thay", "Main thay, Màn thay", "Main thay, Pin thay",
            "Pin thay, Màn thay"
        ])
        pin = st.selectbox("Độ chai Pin (%)", ["100%", "97-99%", "95-96%", "90-94%", "85-89%", "80-84%", "Dưới 80%"])

    with col3:
        st.markdown("### 🌍 Nguồn gốc & BH")
        xuat_xu = st.selectbox("Xuất xứ (Mã VN/A, LL/A...)", ["VN/A", "Mỹ (LL/A)", "Nhật Bản", "Trung Quốc", "ZP/A"])
        bao_hanh = st.selectbox("Chính sách bảo hành", ["Hết bảo hành", "Còn bảo hành", "3 tháng", "4-6 tháng", "7-12 tháng", ">12 tháng"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        predict_btn = st.button("✨ Định giá iphone")

    # Xử lý khi bấm nút dự đoán
    if predict_btn:
        input_df = pd.DataFrame({
            'Dòng máy': [dong_may], 'Phiên bản': [phien_ban], 'Dung lượng (GB)': [dung_luong],
            'Tình trạng': [tinh_trang], 'Tinh_trang_tong_hop': [tinh_trang_chi_tiet],
            'Xuất xứ': [xuat_xu], 'Pin_bucket': [pin], 'Chính sách bảo hành': [bao_hanh]
        })
        
        # Placeholder cho animation loading
        result_placeholder = st.empty()
        
        with result_placeholder.container():
            st.markdown("""
            <div style="text-align: center; padding: 4rem;">
                <h3 style="color: #666; animation: pulse 1.5s infinite;">🧠 AI đang phân tích hàng triệu điểm dữ liệu thị trường...</h3>
                <style>@keyframes pulse { 0% {opacity: 0.5;} 50% {opacity: 1;} 100% {opacity: 0.5;} }</style>
            </div>
            """, unsafe_allow_html=True)
            
        time.sleep(0.8) # Tạo cảm giác AI đang suy nghĩ (UX)
        
        try:
            # Đối với model Best Optimized, ta dùng trực tiếp input_df
            prediction = current_model.predict(input_df)[0]
            
            # Hiển thị kết quả tối giản - Chỉ hiện giá tiền
            result_placeholder.empty()
            with result_placeholder.container():
                st.markdown(f"""
                <div class="result-card">
                    <p style="color: #86868b; font-size: 1.2rem; font-weight: 500; text-transform: uppercase; letter-spacing: 2px;">Giá Ước Tính Thị Trường</p>
                    <div class="price-value">{prediction:,.0f} ₫</div>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
                
        except Exception as e:
            result_placeholder.empty()
            st.error(f"Đã xảy ra lỗi trong quá trình dự đoán: {e}")

st.markdown("<br><br><p style='text-align: center; color: #86868b; font-size: 0.9rem;'>Thiết kế bởi CDIO Team.</p>", unsafe_allow_html=True)
